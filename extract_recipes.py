#!/usr/bin/env python3

import os
import re
import json
import csv
from pathlib import Path

def find_recipe_files(root_dir):
    """Find all Java files that extend Recipe"""
    recipe_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip build directories and other non-source directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'build' and d != 'target']
        
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for classes that extend Recipe
                        if re.search(r'class\s+\w+\s+extends\s+Recipe\b', content) or \
                           re.search(r'class\s+\w+\s+extends\s+ScanningRecipe\b', content):
                            recipe_files.append(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return recipe_files

def extract_recipe_info(file_path):
    """Extract recipe information from a Java file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract class name
        class_match = re.search(r'(?:public\s+)?(?:abstract\s+)?class\s+(\w+)\s+extends\s+(?:Recipe|ScanningRecipe)', content)
        if not class_match:
            return None
        
        class_name = class_match.group(1)
        
        # Extract display name from getDisplayName() method
        display_name_match = re.search(r'getDisplayName\(\)\s*\{\s*return\s+"([^"]+)"', content)
        display_name = display_name_match.group(1) if display_name_match else class_name
        
        # Extract description from getDescription() method
        description_match = re.search(r'getDescription\(\)\s*\{\s*return\s+"([^"]+)"', content)
        description = description_match.group(1) if description_match else ""
        
        # Determine recipe type
        recipe_type = "Java"
        if "Refaster" in content:
            recipe_type = "Refaster"
        
        # Extract options (this is simplified - real implementation would be more complex)
        options = "{}"
        option_matches = re.findall(r'@Option\s*\([^)]+\)\s*(?:\w+\s+)*(\w+)\s+(\w+);', content)
        if option_matches:
            options_dict = {}
            for option_match in option_matches:
                options_dict[option_match[1]] = f"{option_match[0]} field"
            options = json.dumps(options_dict, indent=2)
        
        return {
            'displayName': display_name,
            'description': description,
            'recipeType': recipe_type,
            'sourceCode': content,
            'options': options,
            'className': class_name,
            'filePath': file_path
        }
    
    except Exception as e:
        print(f"Error extracting info from {file_path}: {e}")
        return None

def main():
    # Set the root directory to the rewrite project
    root_dir = "/Users/manethninduwara/Developer/openRewrite/rewrite-all"
    
    print("Scanning for Recipe classes...")
    recipe_files = find_recipe_files(root_dir)
    print(f"Found {len(recipe_files)} recipe files")
    
    recipes_data = []
    
    for file_path in recipe_files:
        print(f"Processing: {file_path}")
        recipe_info = extract_recipe_info(file_path)
        if recipe_info:
            recipes_data.append(recipe_info)
    
    print(f"Extracted information from {len(recipes_data)} recipes")
    
    # Export to CSV
    output_file = "/Users/manethninduwara/Developer/openRewrite/RewriteRecipeSource_all.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Recipe name', 'Recipe description', 'Recipe type', 'Recipe source code', 'Recipe options']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header with descriptions
        writer.writeheader()
        writer.writerow({
            'Recipe name': 'The name of the recipe.',
            'Recipe description': 'The description of the recipe.',
            'Recipe type': 'Differentiate between Java and YAML recipes, as they may be two independent data sets used in LLM fine-tuning.',
            'Recipe source code': 'The full source code of the recipe.',
            'Recipe options': 'JSON format of recipe options.'
        })
        
        # Write data
        for recipe in recipes_data:
            writer.writerow({
                'Recipe name': recipe['displayName'],
                'Recipe description': recipe['description'],
                'Recipe type': recipe['recipeType'],
                'Recipe source code': recipe['sourceCode'],
                'Recipe options': recipe['options']
            })
    
    print(f"Data exported to: {output_file}")
    print(f"Total recipes processed: {len(recipes_data)}")
    
    # Also create a summary JSON file
    summary_file = "/Users/manethninduwara/Developer/openRewrite/recipe_summary_spring.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        summary = {
            'totalRecipes': len(recipes_data),
            'recipeTypes': {},
            'recipes': [
                {
                    'className': recipe['className'],
                    'displayName': recipe['displayName'],
                    'description': recipe['description'],
                    'filePath': recipe['filePath'],
                    'recipeType': recipe['recipeType']
                }
                for recipe in recipes_data
            ]
        }
        
        # Count recipe types
        for recipe in recipes_data:
            recipe_type = recipe['recipeType']
            summary['recipeTypes'][recipe_type] = summary['recipeTypes'].get(recipe_type, 0) + 1
        
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"Summary exported to: {summary_file}")

if __name__ == "__main__":
    main()