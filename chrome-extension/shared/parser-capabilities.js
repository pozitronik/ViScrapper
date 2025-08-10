/**
 * Parser Capability Constants
 * Defines all possible capability flags that parsers can declare
 * These flags control which features and observers are enabled for each parser
 */

// ============================================================================
// JSON-LD TRACKING CAPABILITIES
// ============================================================================

/**
 * Whether to use MutationObserver to track JSON-LD changes
 * When true: Sets up MutationObserver on JSON-LD script element to detect product changes
 * When false: No automatic JSON-LD change tracking (parser may handle this internally)
 * Used by: Victoria's Secret (true), Calvin Klein (true), Tommy Hilfiger (false), Carter's (false)
 */
const JSON_LD_MUTATION_OBSERVER = 'useJsonLdMutationObserver';

/**
 * Whether the parser uses JSON-LD data at all
 * When true: Parser has waitForJsonLd() method and extracts data from JSON-LD
 * When false: Parser doesn't use JSON-LD structured data
 * Used by: All current parsers (true)
 */
const JSON_LD_TRACKING = 'useJsonLdTracking';

// ============================================================================
// NAVIGATION & URL TRACKING CAPABILITIES
// ============================================================================

/**
 * Whether URL changes should trigger product change detection
 * When true: URL changes may indicate different product/variant
 * When false: URL changes are handled internally by parser or ignored
 * Used by: Victoria's Secret (true), Calvin Klein (true), Tommy Hilfiger (false), Carter's (false)
 */
const URL_CHANGE_TRACKING = 'useUrlChangeTracking';

/**
 * Type of navigation the site uses
 * Values:
 * - 'full': Traditional full page reloads
 * - 'spa': Single Page Application with dynamic content loading
 * - 'url-based': URL changes trigger content updates (like Carter's)
 * - 'hybrid': Mix of SPA and full page loads
 */
const URL_NAVIGATION_TYPE = 'urlNavigationType';

// Navigation type values
const NAV_TYPE_FULL = 'full';
const NAV_TYPE_SPA = 'spa';
const NAV_TYPE_URL_BASED = 'url-based';
const NAV_TYPE_HYBRID = 'hybrid';

// ============================================================================
// COLOR OBSERVER CAPABILITIES
// ============================================================================

/**
 * How color change observation is managed
 * Values:
 * - 'external': Content script manages color observer based on parser's setupColorObserver()
 * - 'self-managed': Parser manages its own color observer internally (like Tommy Hilfiger)
 * - 'none': No color observer needed
 */
const COLOR_OBSERVER_MODE = 'colorObserverMode';

// Color observer mode values
const COLOR_MODE_EXTERNAL = 'external';
const COLOR_MODE_SELF_MANAGED = 'self-managed';
const COLOR_MODE_NONE = 'none';

// ============================================================================
// PRODUCT CHANGE DETECTION CAPABILITIES
// ============================================================================

/**
 * How product changes are detected
 * Values:
 * - 'standard': Use default change detection (JSON-LD, URL, etc.)
 * - 'url-sku': Can extract SKU from URL for validation (like Carter's)
 * - 'custom': Parser handles all change detection internally
 * - 'none': No automatic change detection
 */
const PRODUCT_CHANGE_DETECTION = 'productChangeDetection';

// Product change detection values
const CHANGE_DETECTION_STANDARD = 'standard';
const CHANGE_DETECTION_URL_SKU = 'url-sku';
const CHANGE_DETECTION_CUSTOM = 'custom';
const CHANGE_DETECTION_NONE = 'none';

// ============================================================================
// MULTI-COLOR SUPPORT CAPABILITIES
// ============================================================================

/**
 * Whether parser supports bulk multi-color product posting
 * When true: Parser has extractAllColors(), switchToColor(), extractCurrentVariant() methods
 * When false: Parser only supports single color extraction
 * Used by: Calvin Klein (true), Tommy Hilfiger (true), Carter's (true), Victoria's Secret (false)
 */
const SUPPORTS_MULTI_COLOR = 'supportsMultiColor';

// ============================================================================
// SPA REFRESH CAPABILITIES
// ============================================================================

/**
 * Delay in milliseconds before triggering SPA panel refresh after color change
 * Values:
 * - 0: No delay, refresh immediately
 * - null/undefined: No SPA refresh on color change
 * - number: Delay in milliseconds before refresh
 * Used by: Tommy Hilfiger (0), Calvin Klein (1500), others (null)
 */
const SPA_REFRESH_DELAY = 'spaRefreshDelay';

// ============================================================================
// DATA EXTRACTION CAPABILITIES
// ============================================================================

/**
 * Whether parser supports multi-size product extraction
 * When true: Parser can extract size combinations (like Waist x Length)
 * When false: Parser only supports simple size lists
 * Used by: Tommy Hilfiger (true), Victoria's Secret (true), Calvin Klein (true), Carter's (false)
 */
const SUPPORTS_MULTI_SIZE = 'supportsMultiSize';

/**
 * Whether parser needs aggressive image lazy-loading handling
 * When true: Parser needs scroll-based image loading (like Calvin Klein)
 * When false: Images load normally or parser handles internally
 * Used by: Calvin Klein (true), others (false)
 */
const NEEDS_IMAGE_LAZY_LOADING = 'needsImageLazyLoading';

// ============================================================================
// DEFAULT CAPABILITIES
// ============================================================================

/**
 * Default capability configuration for parsers
 * Individual parsers can override specific capabilities as needed
 */
const DEFAULT_CAPABILITIES = {
  [JSON_LD_MUTATION_OBSERVER]: true,
  [JSON_LD_TRACKING]: true,
  [URL_CHANGE_TRACKING]: true,
  [URL_NAVIGATION_TYPE]: NAV_TYPE_FULL,
  [COLOR_OBSERVER_MODE]: COLOR_MODE_EXTERNAL,
  [PRODUCT_CHANGE_DETECTION]: CHANGE_DETECTION_STANDARD,
  [SUPPORTS_MULTI_COLOR]: false,
  [SUPPORTS_MULTI_SIZE]: false,
  [NEEDS_IMAGE_LAZY_LOADING]: false,
  [SPA_REFRESH_DELAY]: null // No SPA refresh by default
};


// ============================================================================
// EXPORTS
// ============================================================================

// Make constants available globally in browser environment
if (typeof window !== 'undefined') {
  // Capability keys
  window.JSON_LD_MUTATION_OBSERVER = JSON_LD_MUTATION_OBSERVER;
  window.JSON_LD_TRACKING = JSON_LD_TRACKING;
  window.URL_CHANGE_TRACKING = URL_CHANGE_TRACKING;
  window.URL_NAVIGATION_TYPE = URL_NAVIGATION_TYPE;
  window.COLOR_OBSERVER_MODE = COLOR_OBSERVER_MODE;
  window.PRODUCT_CHANGE_DETECTION = PRODUCT_CHANGE_DETECTION;
  window.SUPPORTS_MULTI_COLOR = SUPPORTS_MULTI_COLOR;
  window.SUPPORTS_MULTI_SIZE = SUPPORTS_MULTI_SIZE;
  window.NEEDS_IMAGE_LAZY_LOADING = NEEDS_IMAGE_LAZY_LOADING;
  window.SPA_REFRESH_DELAY = SPA_REFRESH_DELAY;
  
  // Navigation type values
  window.NAV_TYPE_FULL = NAV_TYPE_FULL;
  window.NAV_TYPE_SPA = NAV_TYPE_SPA;
  window.NAV_TYPE_URL_BASED = NAV_TYPE_URL_BASED;
  window.NAV_TYPE_HYBRID = NAV_TYPE_HYBRID;
  
  // Color observer mode values
  window.COLOR_MODE_EXTERNAL = COLOR_MODE_EXTERNAL;
  window.COLOR_MODE_SELF_MANAGED = COLOR_MODE_SELF_MANAGED;
  window.COLOR_MODE_NONE = COLOR_MODE_NONE;
  
  // Product change detection values
  window.CHANGE_DETECTION_STANDARD = CHANGE_DETECTION_STANDARD;
  window.CHANGE_DETECTION_URL_SKU = CHANGE_DETECTION_URL_SKU;
  window.CHANGE_DETECTION_CUSTOM = CHANGE_DETECTION_CUSTOM;
  window.CHANGE_DETECTION_NONE = CHANGE_DETECTION_NONE;
  
  // Default configuration
  window.DEFAULT_CAPABILITIES = DEFAULT_CAPABILITIES;
}

// Export for use in Node.js environment (for testing)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    // Capability keys
    JSON_LD_MUTATION_OBSERVER,
    JSON_LD_TRACKING,
    URL_CHANGE_TRACKING,
    URL_NAVIGATION_TYPE,
    COLOR_OBSERVER_MODE,
    PRODUCT_CHANGE_DETECTION,
    SUPPORTS_MULTI_COLOR,
    SUPPORTS_MULTI_SIZE,
    NEEDS_IMAGE_LAZY_LOADING,
    SPA_REFRESH_DELAY,
    
    // Navigation type values
    NAV_TYPE_FULL,
    NAV_TYPE_SPA,
    NAV_TYPE_URL_BASED,
    NAV_TYPE_HYBRID,
    
    // Color observer mode values
    COLOR_MODE_EXTERNAL,
    COLOR_MODE_SELF_MANAGED,
    COLOR_MODE_NONE,
    
    // Product change detection values
    CHANGE_DETECTION_STANDARD,
    CHANGE_DETECTION_URL_SKU,
    CHANGE_DETECTION_CUSTOM,
    CHANGE_DETECTION_NONE,
    
    // Default configuration
    DEFAULT_CAPABILITIES
  };
}