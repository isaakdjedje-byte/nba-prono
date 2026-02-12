#!/usr/bin/env node
/**
 * Generate TypeScript configuration from YAML
 * 
 * This script reads the policy-thresholds.yaml file and generates:
 * 1. TypeScript constants with proper types
 * 2. Zod schemas for validation
 * 3. Type definitions
 * 
 * Usage: node generate-ts-config.js
 * Output: src/lib/config/policy-thresholds.ts
 */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const YAML_PATH = path.join(__dirname, 'policy-thresholds.yaml');
const OUTPUT_PATH = path.join(__dirname, '..', 'nba-prono', 'src', 'lib', 'config', 'policy-thresholds.ts');

function generateTypeScript(config) {
  const timestamp = new Date().toISOString();
  
  return `// =============================================================================
// POLICY THRESHOLDS - TypeScript Configuration
// =============================================================================
// ⚠️  AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
// 
// Generated from: shared-config/policy-thresholds.yaml
// Generated at: ${timestamp}
// Version: ${config.version}
// 
// To modify values, edit the YAML file and run:
//   node shared-config/generate-ts-config.js
// =============================================================================

import { z } from 'zod';

// =============================================================================
// RAW CONFIGURATION VALUES
// =============================================================================

export const POLICY_THRESHOLDS = {
  version: "${config.version}",
  lastUpdated: "${config.last_updated}",
  
  quality: {
    criticalFailureThreshold: ${config.quality.critical_failure_threshold},
    minimumForScoring: ${config.quality.minimum_for_scoring},
    validationRules: {
      completenessWeight: ${config.quality.validation_rules.completeness_weight},
      validityWeight: ${config.quality.validation_rules.validity_weight},
      consistencyWeight: ${config.quality.validation_rules.consistency_weight},
      timelinessWeight: ${config.quality.validation_rules.timeliness_weight},
    },
  },
  
  gates: {
    edgeWinner: {
      threshold: ${config.gates.edge_winner.threshold},
      description: "${config.gates.edge_winner.description}",
    },
    edgeOverUnder: {
      threshold: ${config.gates.edge_over_under.threshold},
      description: "${config.gates.edge_over_under.description}",
    },
    confidence: {
      threshold: ${config.gates.confidence.threshold},
      description: "${config.gates.confidence.description}",
    },
    drift: {
      threshold: ${config.gates.drift.threshold},
      description: "${config.gates.drift.description}",
    },
  },
  
  hardStops: {
    dailyLossCap: {
      value: ${config.hard_stops.daily_loss_cap.value},
      unit: "${config.hard_stops.daily_loss_cap.unit}",
      description: "${config.hard_stops.daily_loss_cap.description}",
    },
    maxConsecutiveLosses: {
      count: ${config.hard_stops.max_consecutive_losses.count},
      description: "${config.hard_stops.max_consecutive_losses.description}",
    },
    maxDrawdown: {
      percent: ${config.hard_stops.max_drawdown.percent},
      windowDays: ${config.hard_stops.max_drawdown.window_days},
      description: "${config.hard_stops.max_drawdown.description}",
    },
    manualHalt: {
      enabled: ${config.hard_stops.manual_halt.enabled},
      description: "${config.hard_stops.manual_halt.description}",
    },
  },
  
  scoring: {
    defaultLineOverUnder: ${config.scoring.default_line_over_under},
    minHistoricalGames: ${config.scoring.min_historical_games},
    maxRetries: ${config.scoring.max_retries},
    retryDelayMs: ${config.scoring.retry_delay_ms},
  },
  
  performance: {
    apiResponseTimeoutMs: ${config.performance.api_response_timeout_ms},
    uiMaxLoadTimeMs: ${config.performance.ui_max_load_time_ms},
    defaultPageSize: ${config.performance.default_page_size},
    maxPageSize: ${config.performance.max_page_size},
    cacheTtlSeconds: ${config.performance.cache_ttl_seconds},
  },
} as const;

// =============================================================================
// ZOD SCHEMAS FOR VALIDATION
// =============================================================================

export const QualityThresholdsSchema = z.object({
  criticalFailureThreshold: z.number().min(0).max(1),
  minimumForScoring: z.number().min(0).max(1),
  validationRules: z.object({
    completenessWeight: z.number(),
    validityWeight: z.number(),
    consistencyWeight: z.number(),
    timelinessWeight: z.number(),
  }),
});

export const GatesThresholdsSchema = z.object({
  edgeWinner: z.object({
    threshold: z.number().min(0).max(1),
    description: z.string(),
  }),
  edgeOverUnder: z.object({
    threshold: z.number().min(0).max(1),
    description: z.string(),
  }),
  confidence: z.object({
    threshold: z.number().min(0).max(1),
    description: z.string(),
  }),
  drift: z.object({
    threshold: z.number().min(0).max(1),
    description: z.string(),
  }),
});

export const HardStopsThresholdsSchema = z.object({
  dailyLossCap: z.object({
    value: z.number(),
    unit: z.enum(["EUR", "PERCENT_BANKROLL"]),
    description: z.string(),
  }),
  maxConsecutiveLosses: z.object({
    count: z.number().int().positive(),
    description: z.string(),
  }),
  maxDrawdown: z.object({
    percent: z.number().min(0).max(1),
    windowDays: z.number().int().positive(),
    description: z.string(),
  }),
  manualHalt: z.object({
    enabled: z.boolean(),
    description: z.string(),
  }),
});

export const PolicyThresholdsSchema = z.object({
  version: z.string(),
  lastUpdated: z.string(),
  quality: QualityThresholdsSchema,
  gates: GatesThresholdsSchema,
  hardStops: HardStopsThresholdsSchema,
  scoring: z.object({
    defaultLineOverUnder: z.number(),
    minHistoricalGames: z.number().int().positive(),
    maxRetries: z.number().int().nonnegative(),
    retryDelayMs: z.number().int().nonnegative(),
  }),
  performance: z.object({
    apiResponseTimeoutMs: z.number().int().positive(),
    uiMaxLoadTimeMs: z.number().int().positive(),
    defaultPageSize: z.number().int().positive(),
    maxPageSize: z.number().int().positive(),
    cacheTtlSeconds: z.number().int().positive(),
  }),
});

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export type QualityThresholds = z.infer<typeof QualityThresholdsSchema>;
export type GatesThresholds = z.infer<typeof GatesThresholdsSchema>;
export type HardStopsThresholds = z.infer<typeof HardStopsThresholdsSchema>;
export type PolicyThresholds = z.infer<typeof PolicyThresholdsSchema>;

// =============================================================================
// VALIDATION FUNCTION
// =============================================================================

/**
 * Validate that runtime configuration matches expected schema
 */
export function validatePolicyThresholds(config: unknown): PolicyThresholds {
  return PolicyThresholdsSchema.parse(config);
}

/**
 * Get threshold with runtime validation
 */
export function getThreshold<T extends keyof typeof POLICY_THRESHOLDS>(
  category: T
): typeof POLICY_THRESHOLDS[T] {
  return POLICY_THRESHOLDS[category];
}

// =============================================================================
// USAGE EXAMPLES
// =============================================================================

// import { POLICY_THRESHOLDS } from '@/lib/config/policy-thresholds';
// 
// // Check quality threshold
// if (failureRate > POLICY_THRESHOLDS.quality.criticalFailureThreshold) {
//   triggerFallback();
// }
//
// // Check gate threshold
// if (edge < POLICY_THRESHOLDS.gates.edgeWinner.threshold) {
//   markGateFailed('edge_insufficient');
// }
`;
}

function main() {
  try {
    console.log('🔄 Generating TypeScript configuration from YAML...');
    
    // Read YAML file
    const yamlContent = fs.readFileSync(YAML_PATH, 'utf8');
    const config = yaml.load(yamlContent);
    
    // Generate TypeScript content
    const tsContent = generateTypeScript(config);
    
    // Ensure output directory exists
    const outputDir = path.dirname(OUTPUT_PATH);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
      console.log(`📁 Created directory: ${outputDir}`);
    }
    
    // Write TypeScript file
    fs.writeFileSync(OUTPUT_PATH, tsContent, 'utf8');
    
    console.log('✅ TypeScript configuration generated successfully!');
    console.log(`📄 Output: ${OUTPUT_PATH}`);
    console.log(`📋 Version: ${config.version}`);
    console.log(`📅 Last updated: ${config.last_updated}`);
    
  } catch (error) {
    console.error('❌ Error generating TypeScript configuration:');
    console.error(error.message);
    process.exit(1);
  }
}

main();
