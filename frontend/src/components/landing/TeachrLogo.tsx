/**
 * Teachr Logo Component using logo.png (light mode) or logo_white.png (dark mode)
 */
import React, { useEffect, useState } from 'react';
import { useTheme } from '../theme/theme-provier';

interface TeachrLogoProps {
  size?: 'small' | 'medium' | 'large';
  color?: string; // Kept for backward compatibility, but not used with image
  className?: string;
}

const TeachrLogo: React.FC<TeachrLogoProps> = ({ 
  size = 'medium', 
  className = '' 
}) => {
  const { theme } = useTheme();
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    const checkDarkMode = () => {
      if (theme === 'dark') {
        setIsDarkMode(true);
      } else if (theme === 'light') {
        setIsDarkMode(false);
      } else if (theme === 'system') {
        // Check if dark class is applied to document root
        setIsDarkMode(document.documentElement.classList.contains('dark'));
      }
    };

    checkDarkMode();

    // Listen for theme changes when using system theme
    if (theme === 'system') {
      const observer = new MutationObserver(checkDarkMode);
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class']
      });

      return () => observer.disconnect();
    }
  }, [theme]);

  const sizeMap = {
    small: '1.5rem',   // 24px
    medium: '2rem',    // 32px
    large: '3rem'      // 48px
  };

  const logoSource = isDarkMode ? '/logo_white.png' : '/logo.png';

  return (
    <img
      src={logoSource}
      alt="Teachr"
      className={className}
      style={{ 
        height: sizeMap[size], 
        width: 'auto'
      }}
    />
  );
};

export default TeachrLogo;

