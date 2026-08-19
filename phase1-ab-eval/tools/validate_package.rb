#!/usr/bin/env ruby
# Validate a Proof Expansion package before queue claim/materialization.

require 'yaml'
require 'json'
require 'optparse'
require 'digest'

options = { judge_role: 'judge_blind', judge_provider: 'micu', judge_model: 'gpt-5.6-sol' }
OptionParser.new do |parser|
  parser.banner = 'Usage: ruby validate_package.rb --package FILE --queue FILE --writer-role NAME --writer-provider P --writer-model M'
  parser.on('--package FILE') { |value| options[:package] = value }
  parser.on('--queue FILE') { |value| options[:queue] = value }
  parser.on('--writer-role NAME') { |value| options[:writer_role] = value }
  parser.on('--writer-provider NAME') { |value| options[:writer_provider] = value }
  parser.on('--writer-model NAME') { |value| options[:writer_model] = value }
  parser.on('--judge-role NAME') { |value| options[:judge_role] = value }
  parser.on('--judge-provider NAME') { |value| options[:judge_provider] = value }
  parser.on('--judge-model NAME') { |value| options[:judge_model] = value }
end.parse!
%I[package queue writer_role writer_provider writer_model].each { |key| abort "missing --#{key.to_s.tr('_', '-')}" unless options[key] }

package = YAML.load_file(options[:package])
queue = YAML.load_file(options[:queue])
errors = []
warnings = []

required = %w[package_id status split source_record selection_record writer_bundle judge_bundle run_policy]
required.each { |key| errors << "missing #{key}" unless package[key].is_a?(Hash) || package[key].is_a?(String) }
package_id = package['package_id']
errors << 'package_id empty' if package_id.to_s.empty?
errors << "package status must be ready, got #{package['status'].inspect}" unless package['status'] == 'ready'

source = package['source_record'] || {}
smoke_only = package.dig('run_policy', 'smoke_only') == true
if smoke_only
  errors << 'smoke package must use evidence_status=not-applicable-smoke' unless source['evidence_status'] == 'not-applicable-smoke'
else
  errors << 'formal package may not use unverified-source' if source['evidence_status'] == 'unverified-source'
  errors << 'formal package requires original_text_obtained=true' unless source['original_text_obtained'] == true
end

approval = package.dig('selection_record', 'human_approval') || {}
if %w[dev eval].include?(package['split'])
  required_approval = package['split'] == 'eval' ? 'approved_for_eval' : 'approved_for_dev'
  errors << "human approval missing #{required_approval}" unless approval[required_approval] == true
end

writer_bundle = package['writer_bundle'] || {}
errors << 'writer_bundle.statement empty' if writer_bundle['statement'].to_s.empty?
# v2: proof_spine（每步 objective/idea/completion_test）取代 v1 的 proof_skeleton 字符串
spine = writer_bundle['proof_spine']
if spine.is_a?(Array) && !spine.empty?
  spine.each_with_index do |step, idx|
    errors << "proof_spine[#{idx}] missing step_id" if step['step_id'].to_s.empty?
    errors << "proof_spine[#{idx}] missing objective" if step['objective'].to_s.empty?
    errors << "proof_spine[#{idx}] missing completion_test" if step['completion_test'].to_s.empty?
  end
  spine_ids = spine.map { |step| step['step_id'].to_s }
  errors << 'duplicate proof_spine step_id' if spine_ids.uniq.length != spine_ids.length
else
  errors << 'writer_bundle.proof_spine must be a non-empty array (each step: step_id/objective/completion_test)'
end
errors << 'writer_bundle.claim_status_convention empty' if writer_bundle['claim_status_convention'].to_s.empty?
errors << 'writer_bundle.writing_discipline empty' if writer_bundle['writing_discipline'].to_s.empty?
errors << 'writer_bundle.closed_book_notice empty' if writer_bundle['closed_book_notice'].to_s.empty?
judge_bundle = package['judge_bundle'] || {}
errors << 'judge_bundle.reference_proof empty' if judge_bundle['reference_proof'].to_s.empty?
errors << 'judge_bundle.key_lemmas empty' unless judge_bundle['key_lemmas'].is_a?(Array) && !judge_bundle['key_lemmas'].empty?
# v2: spine_answer_key 必须覆盖每个脊柱步（judge 判补全度的锚点）
spine_answer_key = judge_bundle['spine_answer_key']
if spine_answer_key.is_a?(Array) && !spine_answer_key.empty?
  keyed = spine_answer_key.map { |row| row['step_id'].to_s }
  spine_ids = spine.is_a?(Array) ? spine.map { |step| step['step_id'].to_s } : []
  missing = spine_ids - keyed
  errors << "spine_answer_key 未覆盖步骤: #{missing.join(',')}" unless missing.empty?
else
  errors << 'judge_bundle.spine_answer_key must be a non-empty array covering proof_spine steps'
end

# v2: 窄缝标定（ready 前必须实测定档；探针题除外）
unless package['probe_only'] == true || package['split'] == 'probe'
  nsc = package['narrow_slot_calibration']
  errors << 'narrow_slot_calibration missing' unless nsc.is_a?(Hash)
  if nsc.is_a?(Hash)
    measured = nsc['measured']
    errors << 'narrow_slot_calibration.measured empty（ready 前必须经裸题/带包预测试定档）' if measured.nil? || measured.to_s.empty?
  end
end
# v2: 去答案化记录（审计：写手包内无关键构造）
dar = package['de_answering_record']
errors << 'de_answering_record missing (stripped/retained)' unless dar.is_a?(Hash) && Array(dar['stripped']).any?

deps = package.dig('writer_bundle', 'allowed_dependencies')
unless deps.is_a?(Array)
  errors << 'writer_bundle.allowed_dependencies must be an array'
  deps = []
end
dep_ids = deps.map { |entry| entry['id'].to_s }
errors << 'dependency id empty' if dep_ids.any?(&:empty?)
errors << 'duplicate dependency id' if dep_ids.uniq.length != dep_ids.length

variants = package.dig('judge_bundle', 'variants')
unless variants.is_a?(Array)
  errors << 'judge_bundle.variants must be an array'
  variants = []
end
variant_ids = variants.map { |entry| entry['variant_id'].to_s }
errors << 'variant id empty' if variant_ids.any?(&:empty?)
errors << 'duplicate variant id' if variant_ids.uniq.length != variant_ids.length
selected = Array(package.dig('run_policy', 'variants_to_run'))
errors << 'run_policy.variants_to_run empty' if selected.empty?
selected.each do |variant_id|
  variant = variants.find { |entry| entry['variant_id'] == variant_id }
  unless variant
    errors << "selected variant #{variant_id} absent"
    next
  end
  errors << "variant #{variant_id} missing expected_outcome" if variant['expected_outcome'].to_s.empty?
  patch = variant['writer_bundle_patch']
  unless patch.is_a?(Hash)
    errors << "variant #{variant_id} missing writer_bundle_patch"
    next
  end
  remove = Array(patch['remove_dependency_ids'])
  errors << "variant #{variant_id} duplicate remove_dependency_ids" if remove.uniq.length != remove.length
  unknown = remove - dep_ids
  errors << "variant #{variant_id} removes unknown dependencies #{unknown.join(',')}" unless unknown.empty?
  %w[replace_statement replace_proof_skeleton replace_proof_spine].each do |field|
    value = patch[field]
    errors << "variant #{variant_id} #{field} must be null or nonempty string" unless value.nil? || (value.is_a?(String) && !value.empty?)
  end
  append = Array(patch['append_allowed_dependencies'])
  append_ids = append.map { |entry| entry['id'].to_s }
  errors << "variant #{variant_id} append dependency id empty" if append_ids.any?(&:empty?)
  remaining = dep_ids - remove
  errors << "variant #{variant_id} append dependency collides" unless (remaining & append_ids).empty? && append_ids.uniq.length == append_ids.length
end

policy = package['run_policy'] || {}
requested_writers = Array(policy['writer_models']).map { |row| "#{row['provider']}/#{row['model']}" }
requested_writer = "#{options[:writer_provider]}/#{options[:writer_model]}"
errors << "package writer route mismatch (expected only #{requested_writer}, got #{requested_writers.join(',')})" unless requested_writers == [requested_writer]
errors << 'package judge role mismatch' unless policy['judge_row'] == options[:judge_role]
errors << 'package judge provider mismatch' unless policy['judge_provider'] == options[:judge_provider]
errors << 'package judge model mismatch' unless policy['judge_model'] == options[:judge_model]

queue_item = Array(queue['queue']).find { |entry| entry['package_id'] == package_id }
if queue_item.nil?
  errors << 'package absent from queue'
else
  errors << "queue split mismatch" unless queue_item['split'] == package['split']
  errors << 'queue writer_models mismatch' unless Array(queue_item['writer_models']) == [requested_writer]
  actual_sha = Digest::SHA256.file(options[:package]).hexdigest
  errors << 'queue package_sha256 mismatch' unless queue_item['package_sha256'] == actual_sha
  errors << 'queue item has active claim' unless queue_item['claim'].nil?
end

payload = {
  'package_id' => package_id,
  'package_sha256' => Digest::SHA256.file(options[:package]).hexdigest,
  'valid' => errors.empty?,
  'errors' => errors,
  'warnings' => warnings,
  'resolved_routes' => {
    'writer_role' => options[:writer_role],
    'writer' => requested_writer,
    'judge_role' => options[:judge_role],
    'judge' => "#{options[:judge_provider]}/#{options[:judge_model]}",
  },
}
puts JSON.pretty_generate(payload)
exit(errors.empty? ? 0 : 2)
