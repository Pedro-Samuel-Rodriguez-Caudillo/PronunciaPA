/**
 * Simple hash-based router for SPA navigation
 * Handles routing between index.html and practice.html
 */

type RouteHandler = () => void;

interface Route {
  path: string;
  handler: RouteHandler;
}

export class Router {
  private routes: Map<string, RouteHandler> = new Map();
  private notFoundHandler: RouteHandler | null = null;

  constructor() {
    window.addEventListener('hashchange', () => this.handleRoute());
    window.addEventListener('load', () => this.handleRoute());
  }

  /**
   * Register a route with its handler
   */
  on(path: string, handler: RouteHandler): Router {
    this.routes.set(path, handler);
    return this;
  }

  /**
   * Set 404 handler
   */
  notFound(handler: RouteHandler): Router {
    this.notFoundHandler = handler;
    return this;
  }

  /**
   * Navigate to a route programmatically
   */
  navigate(path: string): void {
    window.location.hash = path;
  }

  /**
   * Get current route path
   */
  getCurrentPath(): string {
    return window.location.hash.slice(1) || '/';
  }

  /**
   * Handle route changes
   */
  private handleRoute(): void {
    const path = this.getCurrentPath();
    const handler = this.routes.get(path);

    if (handler) {
      handler();
    } else if (this.notFoundHandler) {
      this.notFoundHandler();
    } else {
      console.warn(`No handler found for route: ${path}`);
    }
  }

  /**
   * Initialize router with basic routes
   */
  static init(): Router {
    const router = new Router();
    
    router
      .on('/', () => {
        // Home page - already on index.html
        if (window.location.pathname !== '/' && window.location.pathname !== '/index.html') {
          window.location.href = '/';
        }
      })
      .on('/practice', () => {
        // Practice page
        if (window.location.pathname !== '/practice.html') {
          window.location.href = '/practice.html';
        }
      })
      .notFound(() => {
        console.warn('Route not found, redirecting to home');
        window.location.href = '/';
      });

    return router;
  }
}

// Helper function to create navigation links
export function createNavLink(text: string, route: string): HTMLAnchorElement {
  const link = document.createElement('a');
  link.href = `#${route}`;
  link.textContent = text;
  link.className = 'nav-link';
  
  link.addEventListener('click', (e) => {
    e.preventDefault();
    window.location.hash = route;
  });
  
  return link;
}

// Export singleton instance
export const router = Router.init();
