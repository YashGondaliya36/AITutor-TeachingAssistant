import React, { useState } from 'react';

interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    src: string;
    alt: string;
    placeholder?: string;
    className?: string;
}

/**
 * Lazy-loaded image component with native browser lazy loading
 * Improves LCP and reduces initial page load
 */
export const LazyImage: React.FC<LazyImageProps> = ({
    src,
    alt,
    placeholder = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"%3E%3Crect fill="%23f0f0f0" width="400" height="300"/%3E%3C/svg%3E',
    className = '',
    ...props
}) => {
    const [isLoaded, setIsLoaded] = useState(false);
    const [hasError, setHasError] = useState(false);

    return (
        <div className={`relative ${className}`}>
            {!isLoaded && !hasError && (
                <img
                    src={placeholder}
                    alt=""
                    className="absolute inset-0 w-full h-full object-cover blur-sm"
                    aria-hidden="true"
                />
            )}
            <img
                src={src}
                alt={alt}
                loading="lazy"
                decoding="async"
                onLoad={() => setIsLoaded(true)}
                onError={() => setHasError(true)}
                className={`w-full h-full object-cover transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'
                    }`}
                {...props}
            />
        </div>
    );
};

export default LazyImage;
