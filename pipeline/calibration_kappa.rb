#!/usr/bin/env ruby
# Linear weighted Cohen's kappa for Proof Expansion human-vs-judge calibration.

require 'csv'
require 'json'
require 'optparse'
require 'fileutils'

options = { min_units: 12, main_threshold: 0.60, c_threshold: 0.50 }
OptionParser.new do |parser|
  parser.banner = 'Usage: ruby calibration_kappa.rb --input ratings.csv --output calibration.data.json [options]'
  parser.on('--input PATH', 'CSV ratings file') { |value| options[:input] = value }
  parser.on('--output PATH', 'JSON output') { |value| options[:output] = value }
  parser.on('--min-units N', Integer, 'Minimum complete units per metric') { |value| options[:min_units] = value }
  parser.on('--main-threshold N', Float, 'H/D/R weighted kappa threshold') { |value| options[:main_threshold] = value }
  parser.on('--c-threshold N', Float, 'C weighted kappa threshold') { |value| options[:c_threshold] = value }
end.parse!
abort 'missing --input' unless options[:input]
abort 'missing --output' unless options[:output]

rows = CSV.read(options[:input], headers: true).map(&:to_h)
errors = []
seen = {}
metrics = %w[H D R C]
groups = Hash.new { |hash, key| hash[key] = [] }

rows.each_with_index do |row, index|
  key = [row['unit_id'], row['metric']]
  errors << "row #{index + 2}: duplicate unit_id/metric #{key.join('/')}" if seen[key]
  seen[key] = true
  unless metrics.include?(row['metric'])
    errors << "row #{index + 2}: invalid metric #{row['metric'].inspect}"
    next
  end
  begin
    human = Integer(row['human_score'])
    judge = Integer(row['judge_score'])
    unless (0..4).cover?(human) && (0..4).cover?(judge)
      errors << "row #{index + 2}: score outside 0..4"
      next
    end
    groups[row['metric']] << [human, judge]
  rescue ArgumentError
    errors << "row #{index + 2}: missing/non-integer human_score or judge_score"
  end
end

def weighted_kappa(pairs)
  n = pairs.length.to_f
  return nil if n.zero?
  weights = ->(a, b) { 1.0 - (a - b).abs.to_f / 4.0 }
  observed = pairs.sum { |a, b| weights.call(a, b) } / n
  human = Array.new(5, 0.0)
  judge = Array.new(5, 0.0)
  pairs.each { |a, b| human[a] += 1; judge[b] += 1 }
  expected = 0.0
  5.times do |a|
    5.times do |b|
      expected += (human[a] / n) * (judge[b] / n) * weights.call(a, b)
    end
  end
  return 1.0 if (1.0 - expected).abs < 1e-12 && (observed - expected).abs < 1e-12
  (observed - expected) / (1.0 - expected)
end

per_metric = metrics.to_h do |metric|
  pairs = groups[metric]
  [metric, { 'unit_count' => pairs.length, 'weighted_kappa' => weighted_kappa(pairs) }]
end

thresholds = { 'H' => options[:main_threshold], 'D' => options[:main_threshold], 'R' => options[:main_threshold], 'C' => options[:c_threshold] }
passes = metrics.all? do |metric|
  entry = per_metric[metric]
  entry['unit_count'] >= options[:min_units] && !entry['weighted_kappa'].nil? && entry['weighted_kappa'] >= thresholds[metric]
end
no_main_floor_breach = %w[H D R].all? do |metric|
  value = per_metric[metric]['weighted_kappa']
  !value.nil? && value >= 0.40
end

payload = {
  'input' => File.expand_path(options[:input]),
  'validation' => { 'ok' => errors.empty?, 'errors' => errors },
  'thresholds' => { 'min_units' => options[:min_units], 'main' => options[:main_threshold], 'C' => options[:c_threshold], 'main_floor' => 0.40 },
  'metrics' => per_metric,
  'passed' => errors.empty? && passes && no_main_floor_breach,
}
FileUtils.mkdir_p(File.dirname(File.expand_path(options[:output])))
File.write(options[:output], JSON.pretty_generate(payload) + "\n")
puts options[:output]
exit(payload['passed'] ? 0 : 2)
