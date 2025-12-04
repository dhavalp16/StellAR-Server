    ymin, ymax = min(y_coords), max(y_coords)

    # Normalize to 0-1 for YOLO
    # FIXED: used img_h instead of img_height
    dw = 1.0 / img_w
    dh = 1.0 / img_h 
    
    x_center = (xmin + xmax) / 2.0
    y_center = (ymin + ymax) / 2.0
    w = xmax - xmin
    h = ymax - ymin
    
    return (x_center * dw, y_center * dh, w * dw, h * dh)

def main():
    print("--- Phase 1: Scanning for ALL unique class names ---")
    unique_labels = set()
    
    # Walk through every folder to find every label used
    for root, dirs, files in os.walk(INPUT_ROOT):
        for filename in files:
            if filename.endswith(".json"):
                path = os.path.join(root, filename)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for shape in data.get('shapes', []):
                            # We strip spaces to avoid "Earth " vs "Earth" issues
                            label = shape['label'].strip()
                            unique_labels.add(label)
                except Exception as e:
                    print(f"Error reading {filename}: {e}")

    # Create a sorted Master List
    class_list = sorted(list(unique_labels))
    print(f"Found {len(class_list)} unique classes.")
    print("Classes found:", class_list)
    
    # Save this list 
    classes_file_path = os.path.join(OUTPUT_ROOT, "classes.txt")
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    with open(classes_file_path, "w", encoding='utf-8') as f:
        for idx, name in enumerate(class_list):
            f.write(f"{name}\n")
    print(f"Saved class list to: {classes_file_path}")

    print("\n--- Phase 2: Converting to YOLO format ---")
    
    converted_count = 0
    
    for root, dirs, files in os.walk(INPUT_ROOT):
        for filename in files:
            if filename.endswith(".json"):
                json_path = os.path.join(root, filename)
                
                # 1. Figure out the destination path
                rel_path = os.path.relpath(root, INPUT_ROOT)
                dest_folder = os.path.join(OUTPUT_ROOT, rel_path)
                os.makedirs(dest_folder, exist_ok=True)
                
                # 2. Convert
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    img_w = data['imageWidth']
                    img_h = data['imageHeight']
                    yolo_lines = []
                    
                    for shape in data['shapes']:
                        label = shape['label'].strip()
                        
                        # Find the ID from our Master List
                        if label in class_list:
                            class_id = class_list.index(label)
                            
                            coords = get_yolo_coords(img_w, img_h, shape['points'])
                            
                            # Line: class_id x y w h
                            line = f"{class_id} {coords[0]:.6f} {coords[1]:.6f} {coords[2]:.6f} {coords[3]:.6f}"
                            yolo_lines.append(line)
                            
                    # 3. Save .txt file
                    if yolo_lines:
                        txt_filename = os.path.splitext(filename)[0] + ".txt"
                        save_path = os.path.join(dest_folder, txt_filename)
                        
                        with open(save_path, "w", encoding='utf-8') as out_f:
                            out_f.write("\n".join(yolo_lines))
                        
                        converted_count += 1
                        
                except Exception as e:
                    print(f"Failed to convert {filename}: {e}")

    print(f"\nSuccess! Converted {converted_count} files.")
    print(f"Labels are stored in: {OUTPUT_ROOT}")

if __name__ == "__main__":
    main()