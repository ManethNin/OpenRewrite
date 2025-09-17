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
        
        # Determine recipe type based on content and path
        recipe_type = "Java"
        if "Refaster" in content:
            recipe_type = "Refaster"
        elif "migrate" in file_path.lower():
            recipe_type = "Migration"
        elif "static" in file_path.lower() or "analysis" in file_path.lower():
            recipe_type = "Static Analysis"
        elif "logging" in file_path.lower():
            recipe_type = "Logging"
        elif "spring" in file_path.lower():
            recipe_type = "Spring"
        elif "test" in file_path.lower():
            recipe_type = "Testing"
        
        # Extract options (simplified)
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

def process_repository(repo_path, repo_name):
    """Process a single repository and return recipe data"""
    print(f"\n=== Processing {repo_name} ===")
    print(f"Scanning: {repo_path}")
    
    recipe_files = find_recipe_files(repo_path)
    print(f"Found {len(recipe_files)} recipe files")
    
    recipes_data = []
    
    for file_path in recipe_files:
        print(f"Processing: {os.path.basename(file_path)}")
        recipe_info = extract_recipe_info(file_path)
        if recipe_info:
            recipe_info['repository'] = repo_name
            recipes_data.append(recipe_info)
    
    print(f"Extracted {len(recipes_data)} recipes from {repo_name}")
    return recipes_data

def main():
    # Define all OpenRewrite repositories to scan
    repositories = [
        ("/Users/manethninduwara/Developer/openRewrite/rewrite", "rewrite-core"),
        ("/Users/manethninduwara/Developer/openRewrite/rewrite-spring", "rewrite-spring"),
        ("/Users/manethninduwara/Developer/openRewrite/rewrite-testing-frameworks", "rewrite-testing-frameworks"),
        ("/Users/manethninduwara/Developer/openRewrite/rewrite-migrate-java", "rewrite-migrate-java"),
        ("/Users/manethninduwara/Developer/openRewrite/rewrite-static-analysis", "rewrite-static-analysis"),
        ("/Users/manethninduwara/Developer/openRewrite/rewrite-logging-frameworks", "rewrite-logging-frameworks"),
    ]
    
    all_recipes = []
    repo_summary = {}
    
    for repo_path, repo_name in repositories:
        if os.path.exists(repo_path):
            repo_recipes = process_repository(repo_path, repo_name)
            all_recipes.extend(repo_recipes)
            repo_summary[repo_name] = len(repo_recipes)
        else:
            print(f"Warning: Repository not found: {repo_path}")
    
    print(f"\n{'='*60}")
    print("COMPREHENSIVE RECIPE EXTRACTION SUMMARY")
    print(f"{'='*60}")
    
    for repo_name, count in repo_summary.items():
        print(f"{repo_name:.<40} {count:>4} recipes")
    
    total_recipes = len(all_recipes)
    print(f"{'TOTAL':.<40} {total_recipes:>4} recipes")
    
    # Export comprehensive CSV
    output_file = "/Users/manethninduwara/Developer/openRewrite/RewriteRecipeSource_comprehensive.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Recipe name', 'Recipe description', 'Recipe type', 'Recipe source code', 'Recipe options', 'Repository']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        writer.writerow({
            'Recipe name': 'The name of the recipe.',
            'Recipe description': 'The description of the recipe.',
            'Recipe type': 'Differentiate between recipe types and repositories.',
            'Recipe source code': 'The full source code of the recipe.',
            'Recipe options': 'JSON format of recipe options.',
            'Repository': 'Source repository of the recipe.'
        })
        
        # Write data
        for recipe in all_recipes:
            writer.writerow({
                'Recipe name': recipe['displayName'],
                'Recipe description': recipe['description'],
                'Recipe type': recipe['recipeType'],
                'Recipe source code': recipe['sourceCode'],
                'Recipe options': recipe['options'],
                'Repository': recipe['repository']
            })
    
    print(f"\nComprehensive data exported to: {output_file}")
    
    # Create detailed summary JSON
    summary_file = "/Users/manethninduwara/Developer/openRewrite/comprehensive_recipe_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        summary = {
            'extractionDate': '2025-09-16',
            'totalRecipes': total_recipes,
            'repositorySummary': repo_summary,
            'recipeTypes': {},
            'recipes': [
                {
                    'className': recipe['className'],
                    'displayName': recipe['displayName'],
                    'description': recipe['description'],
                    'recipeType': recipe['recipeType'],
                    'repository': recipe['repository'],
                    'filePath': recipe['filePath']
                }
                for recipe in all_recipes
            ]
        }
        
        # Count recipe types
        for recipe in all_recipes:
            recipe_type = recipe['recipeType']
            summary['recipeTypes'][recipe_type] = summary['recipeTypes'].get(recipe_type, 0) + 1
        
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"Comprehensive summary exported to: {summary_file}")
    
    print(f"\n🎯 FINAL RESULTS:")
    print(f"   📊 Total Recipes: {total_recipes}")
    print(f"   📁 Repositories: {len(repo_summary)}")
    print(f"   📄 CSV Output: {output_file}")
    print(f"   📋 JSON Summary: {summary_file}")

if __name__ == "__main__":
    main()