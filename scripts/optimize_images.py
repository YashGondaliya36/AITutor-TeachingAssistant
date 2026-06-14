#!/usr/bin/env python3
"""
Image Optimization Script
Phase 2: Frontend Foundations - Asset Optimization

Converts images to WebP/AVIF and creates responsive variants.
Significantly reduces bundle size and improves LCP.

Requirements:
    pip install Pillow pillow-avif-plugin

Usage:
    python scripts/optimize_images.py --input public/images --output public/optimized
"""
import os
import sys
from pathlib import Path
from PIL import Image
import argparse
from typing import List, Tuple


# Responsive breakpoints (widths in pixels)
RESPONSIVE_WIDTHS = [320, 640, 768, 1024, 1280, 1920]

# Quality settings
WEBP_QUALITY = 85
AVIF_QUALITY = 75  # AVIF gets better compression, can use lower quality

# Supported input formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif'}


def optimize_image(
    input_path: Path,
    output_dir: Path,
    formats: List[str] = ['webp', 'avif'],
    create_responsive: bool = True
) -> List[Path]:
    """
    Optimize a single image and create format variants.
    
    Args:
        input_path: Path to source image
        output_dir: Directory to save optimized images
        formats: List of formats to generate ('webp', 'avif')
        create_responsive: Whether to create responsive variants
    
    Returns:
        List of paths to generated images
    """
    output_paths = []
    
    try:
        with Image.open(input_path) as img:
            # Convert RGBA to RGB for JPEG-based formats
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            base_name = input_path.stem
            original_width, original_height = img.size
            
            # Determine which widths to generate
            widths_to_generate = [original_width]
            if create_responsive:
                widths_to_generate = [w for w in RESPONSIVE_WIDTHS if w < original_width]
                widths_to_generate.append(original_width)
            
            # Generate variants for each width and format
            for width in widths_to_generate:
                # Calculate proportional height
                aspect_ratio = original_height / original_width
                height = int(width * aspect_ratio)
                
                # Resize if needed
                if width < original_width:
                    resized = img.resize((width, height), Image.Resampling.LANCZOS)
                else:
                    resized = img
                
                # Save in requested formats
                for fmt in formats:
                    if width == original_width:
                        output_name = f"{base_name}.{fmt}"
                    else:
                        output_name = f"{base_name}-{width}w.{fmt}"
                    
                    output_path = output_dir / output_name
                    
                    if fmt == 'webp':
                        resized.save(
                            output_path,
                            'WEBP',
                            quality=WEBP_QUALITY,
                            method=6  # Best compression
                        )
                    elif fmt == 'avif':
                        try:
                            resized.save(
                                output_path,
                                'AVIF',
                                quality=AVIF_QUALITY,
                                speed=4  # Balance between speed and compression
                            )
                        except Exception as e:
                            print(f"  ⚠️  AVIF not supported (install pillow-avif-plugin): {e}")
                            continue
                    
                    output_paths.append(output_path)
                    
                    # Show file size reduction
                    if input_path.exists():
                        original_size = input_path.stat().st_size
                        new_size = output_path.stat().st_size
                        reduction = ((original_size - new_size) / original_size) * 100
                        print(f"  ✓ {output_name}: {new_size // 1024}KB (-{reduction:.1f}%)")
    
    except Exception as e:
        print(f"  ✗ Error processing {input_path.name}: {e}")
        return []
    
    return output_paths


def generate_srcset_html(base_name: str, widths: List[int], format: str = 'webp') -> str:
    """
    Generate HTML srcset attribute for responsive images.
    
    Args:
        base_name: Base filename without extension
        widths: List of available widths
        format: Image format ('webp' or 'avif')
    
    Returns:
        HTML string for <picture> element
    """
    srcset_entries = []
    for width in widths:
        if width == widths[-1]:
            filename = f"{base_name}.{format}"
        else:
            filename = f"{base_name}-{width}w.{format}"
        srcset_entries.append(f"{filename} {width}w")
    
    srcset = ", ".join(srcset_entries)
    
    return f"""
<picture>
  <source type="image/{format}" srcset="{srcset}" sizes="(max-width: 768px) 100vw, 50vw">
  <img src="{base_name}.{format}" alt="Description" loading="lazy" decoding="async">
</picture>
    """


def optimize_directory(
    input_dir: Path,
    output_dir: Path,
    formats: List[str] = ['webp', 'avif'],
    recursive: bool = False
) -> Tuple[int, int]:
    """
    Optimize all images in a directory.
    
    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        formats: Formats to generate
        recursive: Whether to process subdirectories
    
    Returns:
        Tuple of (processed_count, error_count)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    processed = 0
    errors = 0
    
    # Find all images
    pattern = "**/*" if recursive else "*"
    for file_path in input_dir.glob(pattern):
        if file_path.suffix.lower() in SUPPORTED_FORMATS and file_path.is_file():
            print(f"\nProcessing: {file_path.name}")
            
            # Create subdirectory structure if recursive
            if recursive:
                rel_path = file_path.parent.relative_to(input_dir)
                current_output_dir = output_dir / rel_path
                current_output_dir.mkdir(parents=True, exist_ok=True)
            else:
                current_output_dir = output_dir
            
            result = optimize_image(file_path, current_output_dir, formats)
            
            if result:
                processed += 1
            else:
                errors += 1
    
    return processed, errors


def main():
    parser = argparse.ArgumentParser(description='Optimize images for web performance')
    parser.add_argument('--input', '-i', type=str, required=True, help='Input directory')
    parser.add_argument('--output', '-o', type=str, required=True, help='Output directory')
    parser.add_argument('--formats', '-f', nargs='+', default=['webp'], 
                       choices=['webp', 'avif'], help='Output formats')
    parser.add_argument('--recursive', '-r', action='store_true', 
                       help='Process subdirectories recursively')
    parser.add_argument('--no-responsive', action='store_true',
                       help='Skip responsive variants')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)
    
    print(f"🖼️  Image Optimization")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Formats: {', '.join(args.formats)}")
    print(f"Responsive variants: {not args.no_responsive}")
    print("=" * 60)
    
    processed, errors = optimize_directory(
        input_dir,
        output_dir,
        formats=args.formats,
        recursive=args.recursive
    )
    
    print("\n" + "=" * 60)
    print(f"✅ Complete!")
    print(f"Processed: {processed} images")
    if errors:
        print(f"Errors: {errors} images")
    
    print("\n📝 Next steps:")
    print("1. Update image references in your code to use optimized versions")
    print("2. Use <picture> elements with srcset for responsive images")
    print("3. Add loading='lazy' and decoding='async' attributes")
    
    # Generate example usage
    if processed > 0:
        print("\n💡 Example responsive image HTML:")
        print(generate_srcset_html("example-image", RESPONSIVE_WIDTHS[:4], args.formats[0]))


if __name__ == "__main__":
    main()
