/**
 * Shared Site Detection Module
 * Single source of truth for all site detection logic
 * Used by both ParserFactory and UI components
 */

class SiteDetector {
  /**
   * Canonical registry of all supported sites
   * This is the SINGLE source of truth for site support
   */
  static SUPPORTED_SITES = [
    {
      id: 'victoriassecret',
      name: "Victoria's Secret",
      domain: 'victoriassecret.com',
      parserFactory: () => new VictoriasSecretParser(),
      supported: true
    },
    {
      id: 'calvinklein',
      name: 'Calvin Klein',
      domain: 'calvinklein.us',
      parserFactory: () => new CalvinKleinParser(),
      supported: true
    },
    {
      id: 'carters',
      name: "Carter's",
      domain: 'carters.com',
      parserFactory: () => new CartersParser(),
      supported: true
    },
    {
      id: 'tommy',
      name: 'Tommy Hilfiger',
      domain: 'usa.tommy.com',
      parserFactory: () => new TommyHilfigerParser(),
      supported: true
    },
    {
      id: 'hm',
      name: 'H&M',
      domain: 'hm.com',
      parserFactory: () => new HMParser(),
      supported: true
    }
  ];

  /**
   * Detect site from URL
   * @param {string} url - URL to check (default: current page URL)
   * @returns {Object} Site information object
   */
  static detectSite(url = window.location?.href) {
    console.log('SiteDetector: Detecting site for URL:', url);

    if (!url) {
      console.log('SiteDetector: No URL provided');
      return this.getUnsupportedSite();
    }

    // Check each supported site
    for (const site of this.SUPPORTED_SITES) {
      if (url.includes(site.domain)) {
        console.log(`SiteDetector: Matched site: ${site.name} (${site.domain})`);
        return {
          id: site.id,
          name: site.name,
          domain: site.domain,
          supported: site.supported,
          parserFactory: site.parserFactory
        };
      }
    }

    console.log('SiteDetector: No supported site found for URL:', url);
    return this.getUnsupportedSite();
  }

  /**
   * Get site information for unsupported sites
   * @returns {Object} Unsupported site info
   */
  static getUnsupportedSite() {
    return {
      id: 'unsupported',
      name: 'VIParser',
      domain: null,
      supported: false,
      parserFactory: null
    };
  }

  /**
   * Check if a URL is supported
   * @param {string} url - URL to check
   * @returns {boolean} True if supported
   */
  static isSiteSupported(url = window.location?.href) {
    const site = this.detectSite(url);
    return site.supported;
  }

  /**
   * Get list of all supported domains
   * @returns {string[]} Array of supported domains
   */
  static getSupportedDomains() {
    return this.SUPPORTED_SITES.map(site => site.domain);
  }

  /**
   * Get list of all supported sites with metadata
   * @returns {Object[]} Array of site info objects
   */
  static getAllSites() {
    return this.SUPPORTED_SITES.map(site => ({
      id: site.id,
      name: site.name,
      domain: site.domain,
      supported: site.supported
    }));
  }

  /**
   * Create parser for detected site
   * @param {string} url - URL to detect site for
   * @returns {BaseParser|null} Parser instance or null
   */
  static createParser(url = window.location?.href) {
    const site = this.detectSite(url);

    if (!site.supported || !site.parserFactory) {
      console.log('SiteDetector: Cannot create parser for unsupported site');
      return null;
    }

    try {
      console.log(`SiteDetector: Creating parser for ${site.name}`);
      const parser = site.parserFactory();
      console.log(`SiteDetector: Successfully created ${parser.siteName} parser`);
      return parser;
    } catch (error) {
      console.error(`SiteDetector: Failed to create parser for ${site.name}:`, error);
      return null;
    }
  }

  /**
   * For backward compatibility - detect site for UI components
   * Returns site info in format expected by UI
   * @param {string} url - URL to check (for cross-tab detection)
   * @returns {Promise<Object>} Site information
   */
  static async detectSiteForUI(url = null) {
    // If no URL provided, get from active tab (popup/sidepanel context)
    if (!url && typeof chrome !== 'undefined' && chrome.tabs) {
      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url) {
          url = tab.url;
        }
      } catch (error) {
        console.error('SiteDetector: Error getting active tab:', error);
      }
    }

    return this.detectSite(url);
  }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SiteDetector;
}

// Make available globally in browser context
if (typeof window !== 'undefined') {
  window.SiteDetector = SiteDetector;
}