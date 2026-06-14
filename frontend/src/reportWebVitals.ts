import { onCLS, onINP, onLCP } from 'web-vitals';

const reportWebVitals = (onPerfEntry?: (metric: any) => void) => {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    onCLS(onPerfEntry);
    onINP(onPerfEntry);
    onLCP(onPerfEntry);
  } else {
    // Default: Log to console in development
    if (process.env.NODE_ENV === 'development') {
      onCLS(console.log);
      onINP(console.log);
      onLCP(console.log);
    }
  }
};

export default reportWebVitals;
