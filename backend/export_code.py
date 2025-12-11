import os

# Files to ignore
IGNORE_DIRS = {'venv', '__pycache__', '.git', 'migrations'}
# Extensions to include
INCLUDE_EXT = {'.py', '.html', '.css', '.js'}

output_file = 'full_project_code.txt'

with open(output_file, 'w', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk("."):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if any(file.endswith(ext) for ext in INCLUDE_EXT):
                file_path = os.path.join(root, file)
                outfile.write(f"\n\n{'='*50}\n")
                outfile.write(f"FILE: {file_path}\n")
                outfile.write(f"{'='*50}\n\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"Could not read file: {e}")

print(f"Done! All code saved to {output_file}")