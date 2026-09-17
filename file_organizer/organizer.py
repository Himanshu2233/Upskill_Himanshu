# organizer.py — Core logic of the File Organizer
# We use TWO built-in Python modules — no pip install needed!
#
#   os     → lists files, creates folders, checks paths
#   shutil → moves files from one folder to another

import os
import shutil

# ─────────────────────────────────────────
# FILE TYPE CATEGORIES
# ─────────────────────────────────────────
# This dictionary maps a folder name → list of file extensions
# When we find a file, we check its extension against this dict
# to decide which folder to move it into.

FILE_CATEGORIES = {
    'Images':     ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff'],
    'Videos':     ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
    'Audio':      ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    'Documents':  ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.csv'],
    'Code':       ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.ts', '.json', '.xml', '.php'],
    'Archives':   ['.zip', '.rar', '.tar', '.gz', '.7z', '.bz2'],
    'Executables':['.exe', '.msi', '.bat', '.sh', '.apk'],
    'Fonts':      ['.ttf', '.otf', '.woff', '.woff2'],
    'Others':     []   # Catch-all for anything we don't recognize
}


def get_category(filename):
    """
    Given a filename like 'photo.jpg', return its category.
    
    How it works:
    1. os.path.splitext('photo.jpg') → ('photo', '.jpg')
    2. We take the extension '.jpg' and make it lowercase
    3. We loop through FILE_CATEGORIES and check if '.jpg' is in the list
    4. If found, return that category name. If not found, return 'Others'.
    """
    _, ext = os.path.splitext(filename)   # '_' means "I don't need the name part"
    ext = ext.lower()                      # '.JPG' → '.jpg' (case-insensitive)

    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category

    return 'Others'


def organize_directory(directory_path, dry_run=False):
    """
    Main function: scans a folder and moves files into category subfolders.
    
    Parameters:
        directory_path (str): The path to the folder to organize
        dry_run (bool): If True, only PREVIEW moves without actually doing them
    
    Returns:
        A summary dict with stats about what was organized.
    """

    # Check if the folder exists
    if not os.path.isdir(directory_path):
        return {'error': f'"{directory_path}" is not a valid folder path.'}

    moved   = []   # list of files successfully moved
    skipped = []   # list of files skipped (already in a category folder)
    errors  = []   # list of files that had an error

    # os.listdir() gives us a list of filenames in the folder
    all_items = os.listdir(directory_path)

    for item in all_items:
        item_path = os.path.join(directory_path, item)   # Full path to the item

        # Skip folders (we only move FILES, not subfolders)
        if os.path.isdir(item_path):
            skipped.append(f'[folder] {item}')
            continue

        # Skip hidden files (files starting with '.')
        if item.startswith('.'):
            skipped.append(f'[hidden] {item}')
            continue

        # Figure out which category this file belongs to
        category = get_category(item)

        # Create the destination folder path  e.g. /Downloads/Images
        dest_folder = os.path.join(directory_path, category)

        # Create the category folder if it doesn't exist yet
        if not dry_run:
            os.makedirs(dest_folder, exist_ok=True)   # exist_ok=True → no error if folder exists

        # Build the full destination path  e.g. /Downloads/Images/photo.jpg
        dest_path = os.path.join(dest_folder, item)

        try:
            if not dry_run:
                shutil.move(item_path, dest_path)   # Actually move the file!
            moved.append({'file': item, 'category': category})
        except Exception as e:
            errors.append({'file': item, 'error': str(e)})

    return {
        'directory': directory_path,
        'moved':     moved,
        'skipped':   skipped,
        'errors':    errors,
        'dry_run':   dry_run
    }


# ─────────────────────────────────────────
# QUICK TEST — run this file directly
# ─────────────────────────────────────────
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python organizer.py <folder_path>')
        print('Example: python organizer.py C:\\Users\\sahki\\Downloads')
        sys.exit(1)

    path   = sys.argv[1]
    result = organize_directory(path, dry_run=True)   # dry_run=True → just preview

    if 'error' in result:
        print(f'❌ Error: {result["error"]}')
    else:
        print(f'\n📁 Organizing: {result["directory"]}')
        print(f'📋 Files to move: {len(result["moved"])}')
        print(f'⏭️  Files to skip: {len(result["skipped"])}')
        print()
        for item in result['moved']:
            print(f'  → {item["file"]:40s}  [{item["category"]}]')
