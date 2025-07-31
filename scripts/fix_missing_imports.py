#!/usr/bin/env python3
"""Fix missing response model imports in route files"""


def fix_memory_routes():
    """Add missing MemoryResponse model"""
    file_path = "/Users/dro/Documents/second-brain/app/routes/memory_routes.py"

    # Read file
    with open(file_path) as f:
        content = f.read()

    # Find where to insert the model
    import_section_end = content.find('logger = get_logger(__name__)')

    if 'class MemoryResponse' not in content and import_section_end > 0:
        # Add the model definition
        model_def = '''
class MemoryResponse(BaseModel):
    """Memory response model"""
    id: str
    user_id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

'''

        # Insert before logger
        content = content[:import_section_end] + model_def + content[import_section_end:]

        # Write back
        with open(file_path, 'w') as f:
            f.write(content)

        print(f"✅ Fixed {file_path}")

def main():
    """Run fixes"""
    print("Fixing missing imports...")
    fix_memory_routes()
    print("Done!")

if __name__ == "__main__":
    main()
