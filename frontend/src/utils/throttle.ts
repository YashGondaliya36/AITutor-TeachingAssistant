/**
 * Event Throttling and Debouncing Utilities
 * Phase 5: Real-time & WebRTC - Event Throttling
 * 
 * Reduces high-frequency event processing for better performance.
 * Use for: scratchpad drawing, scroll events, resize events, search inputs.
 */

/**
 * Throttle function - executes at most once per interval
 * Use for: scroll events, resize events, continuous drawing
 * 
 * @param func Function to throttle
 * @param delay Minimum time between executions (ms)
 * @returns Throttled function
 */
export function throttle<T extends (...args: any[]) => any>(
    func: T,
    delay: number
): (...args: Parameters<T>) => void {
    let lastCall = 0;
    let timeoutId: NodeJS.Timeout | null = null;

    return function throttled(...args: Parameters<T>) {
        const now = Date.now();
        const timeSinceLastCall = now - lastCall;

        if (timeSinceLastCall >= delay) {
            lastCall = now;
            func(...args);
        } else {
            // Schedule the next call
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
            timeoutId = setTimeout(() => {
                lastCall = Date.now();
                func(...args);
            }, delay - timeSinceLastCall);
        }
    };
}

/**
 * Debounce function - executes after quiet period
 * Use for: search inputs, form validation, API calls
 * 
 * @param func Function to debounce
 * @param delay Wait time after last call (ms)
 * @returns Debounced function
 */
export function debounce<T extends (...args: any[]) => any>(
    func: T,
    delay: number
): (...args: Parameters<T>) => void {
    let timeoutId: NodeJS.Timeout | null = null;

    return function debounced(...args: Parameters<T>) {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }

        timeoutId = setTimeout(() => {
            func(...args);
        }, delay);
    };
}

/**
 * Request Animation Frame throttle - syncs with browser repaints
 * Use for: animations, drawing, visual updates
 * 
 * @param func Function to throttle
 * @returns RAF-throttled function
 */
export function rafThrottle<T extends (...args: any[]) => any>(
    func: T
): (...args: Parameters<T>) => void {
    let rafId: number | null = null;
    let latestArgs: Parameters<T> | null = null;

    return function rafThrottled(...args: Parameters<T>) {
        latestArgs = args;

        if (rafId === null) {
            rafId = requestAnimationFrame(() => {
                if (latestArgs) {
                    func(...latestArgs);
                }
                rafId = null;
                latestArgs = null;
            });
        }
    };
}

/**
 * Adaptive throttle - adjusts delay based on event frequency
 * Use for: unknown event patterns, variable load scenarios
 * 
 * @param func Function to throttle
 * @param minDelay Minimum delay (ms)
 * @param maxDelay Maximum delay (ms)
 * @returns Adaptively throttled function
 */
export function adaptiveThrottle<T extends (...args: any[]) => any>(
    func: T,
    minDelay: number = 16,
    maxDelay: number = 100
): (...args: Parameters<T>) => void {
    let lastCall = 0;
    let callCount = 0;
    let timeoutId: NodeJS.Timeout | null = null;
    let currentDelay = minDelay;

    return function adaptiveThrottled(...args: Parameters<T>) {
        const now = Date.now();
        const timeSinceLastCall = now - lastCall;

        callCount++;

        // Adapt delay based on call frequency
        if (timeSinceLastCall < minDelay) {
            // Very frequent calls - increase delay
            currentDelay = Math.min(currentDelay * 1.5, maxDelay);
        } else if (timeSinceLastCall > maxDelay) {
            // Infrequent calls - reset to minimum
            currentDelay = minDelay;
            callCount = 0;
        }

        if (timeSinceLastCall >= currentDelay) {
            lastCall = now;
            func(...args);
        } else {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
            timeoutId = setTimeout(() => {
                lastCall = Date.now();
                func(...args);
            }, currentDelay);
        }
    };
}

/**
 * React hook for throttled callbacks
 * 
 * @param callback Function to throttle
 * @param delay Throttle delay (ms)
 * @returns Throttled callback
 */
export function useThrottle<T extends (...args: any[]) => any>(
    callback: T,
    delay: number
): (...args: Parameters<T>) => void {
    const [throttledCallback] = React.useState(() => throttle(callback, delay));
    return throttledCallback;
}

/**
 * React hook for debounced callbacks
 * 
 * @param callback Function to debounce
 * @param delay Debounce delay (ms)
 * @returns Debounced callback
 */
export function useDebounce<T extends (...args: any[]) => any>(
    callback: T,
    delay: number
): (...args: Parameters<T>) => void {
    const [debouncedCallback] = React.useState(() => debounce(callback, delay));
    return debouncedCallback;
}

/**
 * React hook for RAF-throttled callbacks
 * 
 * @param callback Function to throttle
 * @returns RAF-throttled callback
 */
export function useRafThrottle<T extends (...args: any[]) => any>(
    callback: T
): (...args: Parameters<T>) => void {
    const [rafCallback] = React.useState(() => rafThrottle(callback));
    return rafCallback;
}

// Re-export React for hooks
import * as React from 'react';

// Usage examples:
/*
// 1. Scratchpad drawing throttle (60 FPS)
const handleDraw = rafThrottle((event: MouseEvent) => {
  // Draw logic here - executes at most once per frame
  ctx.lineTo(event.clientX, event.clientY);
  ctx.stroke();
});

// 2. Search input debounce
const handleSearch = debounce((query: string) => {
  // API call here - executes 300ms after user stops typing
  fetchSearchResults(query);
}, 300);

// 3. Scroll event throttle
const handleScroll = throttle(() => {
  // Scroll logic here - executes at most once per 100ms
  updateScrollPosition();
}, 100);

// 4. React component usage
function SearchComponent() {
  const debouncedSearch = useDebounce((query: string) => {
    api.search(query);
  }, 300);

  return (
    <input onChange={(e) => debouncedSearch(e.target.value)} />
  );
}

// 5. Scratchpad component with RAF throttling
function ScratchpadCanvas() {
  const throttledDraw = useRafThrottle((x: number, y: number) => {
    drawPoint(x, y);
  });

  return (
    <canvas onMouseMove={(e) => throttledDraw(e.clientX, e.clientY)} />
  );
}
*/
