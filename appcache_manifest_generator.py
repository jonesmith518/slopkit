import os
import hashlib
import argparse
import re

def calculate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        data = f.read()
        sha256_hash.update(data)
    return sha256_hash.hexdigest()

def generate_cache_manifest(directory_path, include_payloads=True):
    manifest = ["CACHE MANIFEST"]
    manifest.append("")
    
    for root, _, files in os.walk(directory_path):
        for file in files:
            lower_file = file.lower()
            if lower_file.endswith('.appcache') or lower_file.endswith('.manifest') or lower_file.endswith('.exe') or lower_file.endswith('.py'): 
                continue
            file_path = os.path.join(root, file)

            if not include_payloads and 'payload' in root:
                continue
            file_hash = calculate_file_hash(file_path)
            
            if args.cloudflare_workaround and file == 'index.html':
                file_path = file_path.replace("index.html","")
                if file_path.isspace() or file_path == '':
                    file_path = '/'

            manifest_path = os.path.relpath(file_path, directory_path)
            if manifest_path.isspace() or manifest_path == '' or manifest_path == '.':
                manifest_path = '/'
                
            manifest_path = manifest_path.replace("\\","/")
            manifest.append(manifest_path + " #" + file_hash)

    manifest.append("")
    manifest.append("NETWORK:")
    manifest.append("*")

    return manifest

def update_manifest_tag(directory_path, add_manifest):
    index_html_path = os.path.join(directory_path, "index.html")
    if not os.path.exists(index_html_path):
        print(f"Couldn't find 'index.html' in '{directory_path}'. Skipping manifest tag update.")
        return

    with open(index_html_path, "r") as f:
        content = f.read()

    html_tag_match = re.search(r'<html(\b[^>]*)\s*>', content)
    if not html_tag_match:
        print(f"<html> tag not found in '{index_html_path}'")
        return

    full_tag = html_tag_match.group(0)
    attrs_part = html_tag_match.group(1)
    has_manifest = bool(re.search(r'\bmanifest\b', attrs_part, re.IGNORECASE))

    did_change = False
    if add_manifest and not has_manifest:
        new_tag = '<html manifest="cache.appcache"' + attrs_part.rstrip() + '>'
        content = content.replace(full_tag, new_tag)
        did_change = True
        print(f"Added manifest attribute in '{index_html_path}'")
    elif not add_manifest and has_manifest:
        cleaned_attrs = re.sub(r'\bmanifest\s*=\s*["\'][^"\']*["\']\s*', '', attrs_part, flags=re.IGNORECASE)
        if cleaned_attrs.strip():
            new_tag = '<html' + cleaned_attrs.rstrip() + '>'
        else:
            new_tag = '<html>'
        content = content.replace(full_tag, new_tag)
        did_change = True
        print(f"Removed manifest attribute in '{index_html_path}'")
    else:
        action = "already present" if add_manifest else "nothing to remove"
        print(f"Manifest {action} in '{index_html_path}'")

    if did_change:
        with open(index_html_path, "w") as f:
            f.write(content)

def oswalk_with_depth_limit(directory_path, max_depth):
    initial_depth = directory_path.rstrip(os.path.sep).count(os.path.sep)
    for root, dirs, files in os.walk(directory_path):
        yield root, dirs, files
        current_depth = root.count(os.path.sep)
        relative_depth = current_depth - initial_depth
        if relative_depth >= max_depth:
            del dirs[:]

parser = argparse.ArgumentParser(description="Generate an appcache file.")
parser.add_argument("-d", "--directory-path", nargs='?', default=None,
                    help="The directory to generate the appcache for. (default: find index.html in the current directory, up to 3 deep)")
parser.add_argument("-cf", "--cloudflare-workaround", action="store_true",
                    help="Cloudflare responds with 308 redirect to root when fetching index.html. Causing the appcache to error out.")
parser.add_argument("--update-manifest-tag", action="store_true", default=True,
                    help="Toggle updating the manifest tag in the HTML file (default: True).")
parser.add_argument("--clean", action="store_true",
                    help="Remove the previously generated cache manifest file and the manifest attribute from the HTML file.")
args = parser.parse_args()

if args.directory_path is None:
    index_html_path = None
    for root, _, files in oswalk_with_depth_limit(os.getcwd(), 3):
        if 'index.html' in files:
            index_html_path = os.path.join(root, 'index.html')
            break
        
    if index_html_path is None:
        print("Couldn't find 'index.html' in the current directory or its subdirectories. Please provide a directory path with the -d flag.")
        exit(1)

    user_input = input(f"Found 'index.html' at '{os.path.dirname(index_html_path)}'. Do you want to use this directory? (y/n): ")

    if user_input.lower() != 'y':
        print("No directory path provided. Exiting.")
        exit(1)

    args.directory_path = os.path.dirname(index_html_path)

if args.update_manifest_tag:
    update_manifest_tag(args.directory_path, add_manifest=not args.clean)

if args.clean:
    output_path = os.path.join(args.directory_path, "cache.appcache")
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"Removed cache manifest: '{output_path}'")
else:
    cache_manifest = generate_cache_manifest(args.directory_path)

    output_path = os.path.join(args.directory_path, "cache.appcache")
    output_path = output_path.replace("\\","/")

    with open(output_path, "w") as manifest_file:
        manifest_file.write("\n".join(cache_manifest))

    print(f"Cache manifest generated in path: '{output_path}'")
