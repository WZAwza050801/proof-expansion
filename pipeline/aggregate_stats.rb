#!/usr/bin/env ruby
# Deterministic statistics for Proof Expansion runs.
# Trusted local input only. It never edits raw artefacts; it writes one derived
# aggregate.data.json. See STATISTICS_CONTRACT.md.

require 'yaml'
require 'json'
require 'optparse'
require 'fileutils'

METRICS = {
  'H' => 'gap_honesty_H',
  'D' => 'assumption_dependency_D',
  'R' => 'reviewability_R',
  'C' => 'mathematical_correctness_C',
}.freeze

options = { bootstrap: 10_000, seed: nil }
OptionParser.new do |parser|
  parser.banner = 'Usage: ruby aggregate_stats.rb --run runs/RUN-ID [--output path] [--bootstrap 10000] [--seed N]'
  parser.on('--run DIR', 'Run directory') { |value| options[:run] = value }
  parser.on('--output PATH', 'Derived JSON output path') { |value| options[:output] = value }
  parser.on('--bootstrap N', Integer, 'Bootstrap draws') { |value| options[:bootstrap] = value }
  parser.on('--seed N', Integer, 'Deterministic random seed') { |value| options[:seed] = value }
end.parse!

abort 'missing --run' unless options[:run]
run_dir = File.expand_path(options[:run])
manifest_path = File.join(run_dir, 'manifest.yml')
abort "missing manifest: #{manifest_path}" unless File.file?(manifest_path)
manifest = YAML.load_file(manifest_path)
abort 'manifest.submissions must be an array' unless manifest['submissions'].is_a?(Array)
seed = options[:seed] || manifest.dig('randomization', 'seed').to_i
seed = 1 if seed.zero?
output_path = File.expand_path(options[:output] || File.join(run_dir, 'aggregate.data.json'))

validation = {
  'ok' => true,
  'errors' => [],
  'warnings' => [],
  'invalid_pairs' => [],
  'unscorable_submissions' => [],
  'anonymity_failures' => [],
}
submissions = manifest['submissions']
private_ids = submissions.map { |row| row['private_id'].to_s }
anonymous_ids = submissions.map { |row| row['anonymous_id'].to_s }
validation['errors'] << 'duplicate private_id' if private_ids.uniq.length != private_ids.length
validation['errors'] << 'duplicate anonymous_id' if anonymous_ids.uniq.length != anonymous_ids.length

permutation = manifest.dig('randomization', 'permutation')
unless permutation.is_a?(Array) && permutation.length == submissions.length
  validation['errors'] << 'randomization.permutation missing or wrong length'
else
  mapped_private = permutation.map { |row| row['private_id'].to_s }.sort
  mapped_anonymous = permutation.map { |row| row['anonymous_id'].to_s }.sort
  validation['errors'] << 'permutation private ids do not match submissions' unless mapped_private == private_ids.sort
  validation['errors'] << 'permutation anonymous ids do not match submissions' unless mapped_anonymous == anonymous_ids.sort
end

records = []
submissions.each do |submission|
  required = %w[private_id anonymous_id condition pair_id problem_id variant_id repetition writer judge prompt artefacts]
  missing = required.reject { |key| submission.key?(key) && !submission[key].nil? && submission[key].to_s != '' }
  validation['errors'] << "submission #{submission['private_id'] || '?'} missing #{missing.join(',')}" unless missing.empty?
  next unless missing.empty?

  prompt_meta = submission['prompt']
  artefacts = submission['artefacts']
  nested_required = %w[materialized_bundle_sha256 selected_variant_record_sha256 judge_bundle_sha256 judge_input_non_submission_sha256]
  nested_missing = nested_required.reject { |key| prompt_meta.is_a?(Hash) && prompt_meta[key] && prompt_meta[key].to_s != '' }
  nested_missing.concat(%w[review_path anonymous_input_path].reject { |key| artefacts.is_a?(Hash) && artefacts[key] && artefacts[key].to_s != '' })
  unless nested_missing.empty?
    validation['errors'] << "submission #{submission['private_id']} missing nested #{nested_missing.join(',')}"
    next
  end

  expected_judge = manifest.dig('routing', 'judge') || {}
  judge = submission['judge']
  unless judge.is_a?(Hash) && judge['actual_provider'] == expected_judge['provider'] && judge['actual_model'] == expected_judge['model']
    validation['errors'] << "judge route mismatch #{submission['private_id']}"
    next
  end
  writer = submission['writer']
  unless writer.is_a?(Hash) && writer['actual_provider'] == writer['provider'] && writer['actual_model'] == writer['model']
    validation['errors'] << "writer route mismatch #{submission['private_id']}"
    next
  end

  review_path = File.join(run_dir, artefacts['review_path'])
  anonymous_path = File.join(run_dir, artefacts['anonymous_input_path'])
  unless File.file?(review_path)
    validation['errors'] << "missing review #{submission['private_id']}: #{submission['review_path']}"
    next
  end
  unless File.file?(anonymous_path)
    validation['errors'] << "missing anonymous input #{submission['private_id']}: #{submission['anonymous_input_path']}"
    next
  end

  anonymous_text = File.read(anonymous_path)
  forbidden = [submission['private_id'].to_s, 'condition:', '"condition"']
  leaked = forbidden.select { |token| !token.empty? && anonymous_text.include?(token) }
  unless leaked.empty?
    validation['anonymity_failures'] << { 'private_id' => submission['private_id'], 'tokens' => leaked }
    next
  end

  begin
    review = JSON.parse(File.read(review_path))
  rescue JSON::ParserError => error
    validation['errors'] << "invalid JSON review #{submission['private_id']}: #{error.message}"
    next
  end
  scores = review['scores']
  unless scores.is_a?(Hash) && METRICS.values.all? { |name| scores[name].is_a?(Numeric) }
    validation['errors'] << "review #{submission['private_id']} lacks required H/D/R/C scores"
    next
  end
  unless METRICS.values.all? { |name| (0..4).cover?(scores[name]) }
    validation['errors'] << "review #{submission['private_id']} score outside 0..4"
    next
  end

  blocking_unverified = Array(review['step_audit']).any? do |step|
    step['status'] == 'judge_unverified' && step['impact'] == 'blocks_main_conclusion'
  end
  if blocking_unverified
    validation['unscorable_submissions'] << submission['private_id']
  end

  records << submission.merge(
    '_review' => review,
    '_scores' => METRICS.transform_values { |score_key| scores[score_key].to_f },
    '_unscorable' => blocking_unverified,
    '_model_key' => "#{submission.dig('writer', 'provider')}/#{submission.dig('writer', 'model')}",
  )
end

validation['errors'].concat(validation['anonymity_failures'].map { |row| "anonymous leakage #{row['private_id']}: #{row['tokens'].join(',')}" })
pairs = records.group_by { |row| row['pair_id'] }
valid_pairs = []

pairs.each do |pair_id, rows|
  conditions = rows.map { |row| row['condition'] }.sort
  invalid_reasons = []
  invalid_reasons << 'must contain exactly A and B' unless conditions == %w[A B]
  keys = rows.map { |row| [row['problem_id'], row['variant_id'], row['repetition'], row['_model_key'], row.dig('writer', 'max_tokens'), row.dig('prompt', 'materialized_bundle_sha256'), row.dig('prompt', 'selected_variant_record_sha256'), row.dig('prompt', 'judge_bundle_sha256'), row.dig('prompt', 'judge_input_non_submission_sha256')] }.uniq
  invalid_reasons << 'paired metadata differs' unless keys.length == 1
  invalid_reasons << 'contains unscorable judge result' if rows.any? { |row| row['_unscorable'] }
  if invalid_reasons.empty?
    a = rows.find { |row| row['condition'] == 'A' }
    b = rows.find { |row| row['condition'] == 'B' }
    diff = METRICS.keys.to_h { |metric| [metric, b['_scores'][metric] - a['_scores'][metric]] }
    valid_pairs << {
      'pair_id' => pair_id,
      'problem_id' => a['problem_id'],
      'variant_id' => a['variant_id'],
      'repetition' => a['repetition'],
      'model_key' => a['_model_key'],
      'diff' => diff,
      'a' => a,
      'b' => b,
    }
  else
    validation['invalid_pairs'] << { 'pair_id' => pair_id, 'reasons' => invalid_reasons }
  end
end

validation['ok'] = validation['errors'].empty? && validation['invalid_pairs'].empty? && validation['unscorable_submissions'].empty?

def mean(values)
  values.sum.to_f / values.length
end

def percentile(sorted, q)
  sorted[(q * (sorted.length - 1)).round]
end

def bootstrap(values, draws, rng)
  return nil if values.length < 2
  samples = Array.new(draws) do
    mean(Array.new(values.length) { values[rng.rand(values.length)] })
  end.sort
  { 'lower' => percentile(samples, 0.025), 'upper' => percentile(samples, 0.975) }
end

rng = Random.new(seed)
models = {}
valid_pairs.group_by { |pair| pair['model_key'] }.each do |model_key, model_pairs|
  # repetition means within each problem×variant
  variant_means = {}
  model_pairs.group_by { |pair| [pair['problem_id'], pair['variant_id']] }.each do |key, rows|
    variant_means[key] = METRICS.keys.to_h do |metric|
      [metric, mean(rows.map { |row| row['diff'][metric] })]
    end
  end
  # equal-weight variants within problem: one cluster vector per problem
  problem_values = {}
  variant_means.group_by { |(problem_id, _variant_id), _value| problem_id }.each do |problem_id, entries|
    problem_values[problem_id] = METRICS.keys.to_h do |metric|
      [metric, mean(entries.map { |_key, values| values[metric] })]
    end
  end
  metrics = METRICS.keys.to_h do |metric|
    values = problem_values.values.map { |row| row[metric] }
    ci = bootstrap(values, options[:bootstrap], rng)
    [metric, {
      'pair_count' => model_pairs.length,
      'variant_cluster_count' => variant_means.length,
      'problem_cluster_count' => values.length,
      'mean_diff' => values.empty? ? nil : mean(values),
      'ci95' => ci,
      'estimable' => !ci.nil?,
      'problem_values' => problem_values.transform_values { |row| row[metric] },
    }]
  end
  models[model_key] = { 'metrics' => metrics }
end

failure_modes = %w[fabricated_dependency hidden_gap assumption_drift conditional_overclaim false_skip]
rate_data = {}
%w[A B].each do |condition|
  scored = valid_pairs.flat_map { |pair| [pair['a'], pair['b']] }.select { |row| row['condition'] == condition }
  counts = failure_modes.to_h { |mode| [mode, 0] }
  scored.each do |row|
    Array(row['_review']['failure_modes']).each { |mode| counts[mode] += 1 if counts.key?(mode) }
  end
  rate_data[condition] = {
    'denominator_valid_submissions' => scored.length,
    'counts' => counts,
    'rates' => counts.transform_values { |count| scored.empty? ? nil : count.to_f / scored.length },
  }
end

payload = {
  'run_id' => manifest['run_id'],
  'split' => manifest['split'],
  'validation' => validation,
  'bootstrap' => {
    'cluster_unit' => 'problem-level equal-weight mean over selected variants; repetitions averaged within variant',
    'draws' => options[:bootstrap],
    'seed' => seed,
    'ci' => 'percentile 2.5%..97.5%',
  },
  'models' => models,
  'failure_mode_rates' => rate_data,
}
FileUtils.mkdir_p(File.dirname(output_path))
File.write(output_path, JSON.pretty_generate(payload) + "\n")
puts output_path
exit(validation['ok'] ? 0 : 2)
