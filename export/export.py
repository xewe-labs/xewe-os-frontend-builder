import os
import shutil
import datetime
import argparse
import re

def process_flask_to_arduino(input_path, output_path):
    # Ensure absolute paths
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)

    if not os.path.exists(input_path):
        print(f"Error: Input path '{input_path}' does not exist.")
        return

    # 1. Spits out project name
    project_basename = os.path.basename(input_path)
    print(f"Project Name: {project_basename}")

    # 2. Setup final output path with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output_dir = os.path.join(output_path, f"{project_basename}_{timestamp}")

    os.makedirs(final_output_dir, exist_ok=True)
    print(f"Output Directory: {final_output_dir}")

    # Store tuples of (include_path, var_name, web_route, mime_type)
    generated_files_info = []

    # MIME Type mapping
    mime_types = {
        'html': 'text/html',
        'css': 'text/css',
        'js': 'application/javascript'
    }

    # 3. Process templates/ and static/ while preserving paths
    target_dirs = ['templates', 'static']

    for directory in target_dirs:
        dir_path = os.path.join(input_path, directory)
        if not os.path.exists(dir_path):
            continue

        for root, _, files in os.walk(dir_path):
            # Calculate the relative path from the input project root
            rel_dir = os.path.relpath(root, input_path)

            # Create corresponding directories in the output folder
            out_dir_path = os.path.join(final_output_dir, rel_dir)
            os.makedirs(out_dir_path, exist_ok=True)

            for file in files:
                # Only care about html, js, and css
                if not file.endswith(('.html', '.js', '.css')):
                    continue

                file_path = os.path.join(root, file)
                name, ext = os.path.splitext(file)
                ext = ext.lstrip('.')  # Remove the dot

                # Determine MIME type
                mime_type = mime_types.get(ext, 'text/plain')

                # Make names C++ compliant (e.g., replace hyphens with underscores)
                safe_name = name.replace('-', '_').replace('.', '_')
                h_filename = f"{safe_name}_{ext}.h"
                var_name = f"{safe_name.upper()}_{ext.upper()}"

                # Calculate the exact web route the browser will ask for
                if directory == 'templates' and file == 'index.html':
                    web_route = "/"
                else:
                    # e.g., /static/calendar-utils.js
                    route_path = os.path.join(rel_dir, file).replace(os.sep, '/')
                    web_route = f"/{route_path}"

                # Read original web file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    print(f"Skipping binary/non-utf8 file: {file_path}")
                    continue

                # --- THE JINJA2 KILLER ---
                # Replaces {{ url_for('static', filename='style.css') }} with /static/style.css
                jinja_pattern = r"\{\{\s*url_for\(['\"]static['\"]\s*,\s*filename=['\"](.+?)['\"]\)\s*\}\}"
                content = re.sub(jinja_pattern, r"/static/\1", content)
                # -------------------------

                # Write Arduino .h file inside the preserved directory structure
                h_filepath = os.path.join(out_dir_path, h_filename)
                with open(h_filepath, 'w', encoding='utf-8') as f:
                    f.write("#pragma once\n")
                    f.write("#include <pgmspace.h>\n")
                    f.write(f"static const char {var_name}[] PROGMEM = R\"rawliteral(\n")
                    f.write(content)
                    # Ensure trailing newline before closing the literal
                    if not content.endswith('\n'):
                        f.write("\n")
                    f.write(")rawliteral\";\n")

                # Build the include path using forward slashes for C++ compatibility
                include_path = os.path.join(rel_dir, h_filename).replace(os.sep, '/')
                generated_files_info.append((include_path, var_name, web_route, mime_type))

    # 4. Copy app.py for LLM processing
    app_py_path = os.path.join(input_path, 'app.py')
    if os.path.exists(app_py_path):
        shutil.copy2(app_py_path, os.path.join(final_output_dir, 'app.py'))
        print("Copied app.py successfully.")

    # 5. Generate dirname_app.ino with auto-wiring
    ino_filename = f"{project_basename}_app.ino"
    ino_filepath = os.path.join(final_output_dir, ino_filename)

    with open(ino_filepath, 'w', encoding='utf-8') as f:
        f.write("#include <WiFi.h>\n")
        f.write("#include <WebServer.h>\n\n")
        f.write("WebServer server(80);\n\n")

        # Include all generated headers
        f.write("// --- Auto-Generated Web Files ---\n")
        for include_path, var_name, _, _ in generated_files_info:
            f.write(f'#include "{include_path}"\n')
        f.write("// --------------------------------\n\n")

        f.write("void setupRoutes() {\n")
        f.write("  // --- Auto-Generated Routes ---\n")
        for _, var_name, web_route, mime_type in generated_files_info:
            # Wire up the server.on calls automatically using the exact expected file names
            f.write(f'  server.on("{web_route}", HTTP_GET, []() {{\n')
            f.write(f'    server.sendHeader("Access-Control-Allow-Origin", "*");\n')
            f.write(f'    server.send_P(200, "{mime_type}", {var_name});\n')
            f.write(f'  }});\n')
        f.write("}\n\n")

        f.write("void setup() {\n")
        f.write("  Serial.begin(115200);\n")
        f.write("  // TODO: Setup WiFi here\n\n")
        f.write("  setupRoutes();\n")
        f.write("  server.begin();\n")
        f.write("}\n\n")

        f.write("void loop() {\n")
        f.write("  server.handleClient();\n")
        f.write("}\n")

    print(f"Successfully generated {len(generated_files_info)} header files and {ino_filename}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Flask static/templates to Arduino headers.")
    parser.add_argument("input_path", help="Path to the Flask project root")
    parser.add_argument("output_path", help="Path where the output folder should be created")

    args = parser.parse_args()
    process_flask_to_arduino(args.input_path, args.output_path)