#!/usr/bin/env python3
"""
Script to replace print() statements with proper logging
Run from project root: python scripts/fix_logging.py
"""
import os
import re
from pathlib import Path

# Files to skip
SKIP_FILES = {
    'fix_logging.py',
    'run_all_migrations.py',  # Keep print for user interaction
    '__pycache__',
    '.git',
    'node_modules',
    'venv',
}

# Patterns to replace
PATTERNS = [
    (r'print\(f"❌', 'logger.error(f"'),
    (r'print\(f"⚠️', 'logger.warning(f"'),
    (r'print\(f"✅', 'logger.info(f"'),
    (r'print\(f"🔹', 'logger.info(f"'),
    (r'print\("❌', 'logger.error("'),
    (r'print\("⚠️', 'logger.warning("'),
    (r'print\("✅', 'logger.info("'),
    (r'print\(f"Error', 'logger.error(f"Error'),
    (r'print\(f"Failed', 'logger.error(f"Failed'),
    (r'print\(f"Warning', 'logger.warning(f"Warning'),
    (r'print\("Error', 'logger.error("Error'),
    (r'print\("Failed', 'logger.error("Failed'),
    (r'print\("Warning', 'logger.warning("Warning'),
]

def should_skip(filepath):
    """Check if file should be skipped"""
    return any(skip in str(filepath) for skip in SKIP_FILES)

def needs_logger_import(content):
    """Check if file needs logger import"""
    return 'logger.' in content and 'from shared.logging_config import get_logger' not in content

def add_logger_import(content, filename):
    """Add logger import and initialization"""
    # Find the last import statement
    lines = content.split('\n')
    last_import_idx = 0
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i
    
    # Add logger import after last import
    logger_import = '\nfrom shared.logging_config import get_logger\n'
    logger_init = f'logger = get_logger(__name__)\n'
    
    lines.insert(last_import_idx + 1, logger_import)
    lines.insert(last_import_idx + 2, logger_init)
    
    return '\n'.join(lines)

def fix_file(filepath):
    """Fix logging in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply replacements
        for pattern, replacement in PATTERNS:
            content = re.sub(pattern, replacement, content)
        
        # Add logger import if needed
        if needs_logger_import(content):
            content = add_logger_import(content, filepath.name)
        
        # Only write if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function"""
    services_dir = Path('services')
    managers_dir = Path('managers')
    
    fixed_count = 0
    
    # Process services directory
    for filepath in services_dir.rglob('*.py'):
        if should_skip(filepath):
            continue
        
        if fix_file(filepath):
            print(f"✅ Fixed: {filepath}")
            fixed_count += 1
    
    # Process managers directory
    if managers_dir.exists():
        for filepath in managers_dir.rglob('*.py'):
            if should_skip(filepath):
                continue
            
            if fix_file(filepath):
                print(f"✅ Fixed: {filepath}")
                fixed_count += 1
    
    print(f"\n🎉 Fixed {fixed_count} files")
    print("\nNext steps:")
    print("1. Review changes: git diff")
    print("2. Test services: python services/TeachingAssistant/api.py")
    print("3. Commit: git add -A && git commit -m 'fix: Replace print with logger'")

if __name__ == '__main__':
    main()
