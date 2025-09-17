#!/usr/bin/env python3

import csv
import json
from pathlib import Path

def convert_csv_to_json(csv_file_path, json_file_path):
    """Convert CSV recipe data to structured JSON format"""
    
    recipes = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row_num, row in enumerate(reader):
            # Skip the header description row
            if row_num == 0 and row['Recipe name'] == 'The name of the recipe.':
                continue
            
            # Parse recipe options (if it's valid JSON)
            try:
                options = json.loads(row['Recipe options']) if row['Recipe options'].strip() else {}
            except json.JSONDecodeError:
                options = {}
            
            recipe = {
                "id": row_num,  # Add unique ID
                "name": row['Recipe name'],
                "description": row['Recipe description'],
                "type": row['Recipe type'],
                "sourceCode": row['Recipe source code'],
                "options": options,
                "repository": row.get('Repository', 'unknown'),  # Handle files with/without repository column
                "metadata": {
                    "sourceCodeLength": len(row['Recipe source code']),
                    "hasDescription": bool(row['Recipe description'].strip()),
                    "hasOptions": bool(options),
                    "estimatedTokens": len(row['Recipe source code']) // 4  # Rough estimate
                }
            }
            
            recipes.append(recipe)
    
    # Create structured output with metadata
    output = {
        "metadata": {
            "extractionDate": "2025-09-16",
            "totalRecipes": len(recipes),
            "sourceFormat": "OpenRewrite Recipe Collection",
            "description": "Comprehensive collection of OpenRewrite recipes for Java code transformation and repair"
        },
        "statistics": generate_statistics(recipes),
        "recipes": recipes
    }
    
    # Write to JSON file
    with open(json_file_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(output, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"✅ Converted {len(recipes)} recipes to JSON")
    print(f"📄 Output file: {json_file_path}")
    return output

def generate_statistics(recipes):
    """Generate statistics about the recipe collection"""
    
    stats = {
        "totalRecipes": len(recipes),
        "recipeTypes": {},
        "repositories": {},
        "averageSourceCodeLength": 0,
        "totalSourceCodeLength": 0,
        "recipesWithDescriptions": 0,
        "recipesWithOptions": 0,
        "estimatedTotalTokens": 0
    }
    
    total_length = 0
    
    for recipe in recipes:
        # Count by type
        recipe_type = recipe["type"]
        stats["recipeTypes"][recipe_type] = stats["recipeTypes"].get(recipe_type, 0) + 1
        
        # Count by repository
        repository = recipe["repository"]
        stats["repositories"][repository] = stats["repositories"].get(repository, 0) + 1
        
        # Calculate lengths and counts
        source_length = len(recipe["sourceCode"])
        total_length += source_length
        
        if recipe["description"].strip():
            stats["recipesWithDescriptions"] += 1
        
        if recipe["options"]:
            stats["recipesWithOptions"] += 1
        
        stats["estimatedTotalTokens"] += recipe["metadata"]["estimatedTokens"]
    
    stats["averageSourceCodeLength"] = total_length // len(recipes) if recipes else 0
    stats["totalSourceCodeLength"] = total_length
    
    return stats

def create_training_format(recipes, output_file):
    """Create a simplified format optimized for LLM training"""
    
    training_data = []
    
    for recipe in recipes:
        training_example = {
            "instruction": f"Create a recipe that {recipe['description'].lower()}",
            "input": f"Recipe type: {recipe['type']}",
            "output": recipe['sourceCode'],
            "metadata": {
                "recipeName": recipe['name'],
                "recipeType": recipe['type'],
                "repository": recipe['repository']
            }
        }
        training_data.append(training_example)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "format": "instruction_tuning",
                "description": "OpenRewrite recipes formatted for LLM fine-tuning",
                "totalExamples": len(training_data)
            },
            "data": training_data
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created training format with {len(training_data)} examples")
    print(f"📄 Training file: {output_file}")

def main():
    # Define file paths
    base_path = Path("/Users/manethninduwara/Developer/openRewrite")
    
    # Convert the comprehensive CSV (898 recipes)
    comprehensive_csv = base_path / "RewriteRecipeSource_comprehensive.csv"
    comprehensive_json = base_path / "RewriteRecipeSource_comprehensive.json"
    
    # Also convert the smaller CSV from attachment (3 recipes from rewrite-all)
    small_csv = base_path / "RewriteRecipeSource_all.csv"
    small_json = base_path / "RewriteRecipeSource_all.json"
    
    print("🔄 Converting OpenRewrite Recipe CSV files to JSON...")
    
    # Convert comprehensive dataset
    if comprehensive_csv.exists():
        print(f"\n📊 Converting comprehensive dataset: {comprehensive_csv}")
        comprehensive_data = convert_csv_to_json(comprehensive_csv, comprehensive_json)
        
        # Create training format
        training_json = base_path / "RewriteRecipes_training_format.json"
        create_training_format(comprehensive_data["recipes"], training_json)
        
        print(f"\n📈 COMPREHENSIVE DATASET STATS:")
        stats = comprehensive_data["statistics"]
        print(f"   Total Recipes: {stats['totalRecipes']}")
        print(f"   Recipe Types: {len(stats['recipeTypes'])}")
        print(f"   Repositories: {len(stats['repositories'])}")
        print(f"   Avg Source Length: {stats['averageSourceCodeLength']:,} chars")
        print(f"   Estimated Tokens: {stats['estimatedTotalTokens']:,}")
        
    else:
        print(f"❌ Comprehensive CSV not found: {comprehensive_csv}")
    
    # Convert smaller dataset from attachment
    if small_csv.exists():
        print(f"\n📊 Converting small dataset: {small_csv}")
        convert_csv_to_json(small_csv, small_json)
    else:
        print(f"❌ Small CSV not found: {small_csv}")
    
    print(f"\n🎯 JSON conversion complete!")
    print(f"   📁 Output directory: {base_path}")
    print(f"   📄 Files created: *.json")

if __name__ == "__main__":
    main()