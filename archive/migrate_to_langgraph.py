#!/usr/bin/env python3
"""
LangGraph Migration Script
Automated migration from custom implementation to LangGraph

Usage:
    python migrate_to_langgraph.py --step [1-4]
    python migrate_to_langgraph.py --full  # Run all steps
    python migrate_to_langgraph.py --rollback  # Rollback migration
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

class LangGraphMigrator:
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "migration_backup"
        self.services_dir = self.project_root / "app" / "services"
        self.legacy_dir = self.services_dir / "legacy"
        
    def log(self, message: str, level: str = "INFO"):
        """Log migration progress"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def create_backup(self):
        """Create full backup before migration"""
        self.log("Creating full project backup...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        # Backup critical files
        backup_files = [
            "app/services/",
            "app/api/routes.py",
            "app/main.py",
            "requirements.txt",
            "tests/"
        ]
        
        self.backup_dir.mkdir(exist_ok=True)
        
        for file_path in backup_files:
            src = self.project_root / file_path
            dst = self.backup_dir / file_path
            
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
        
        self.log("Backup created successfully")
    
    def step1_install_dependencies(self):
        """Step 1: Install LangGraph dependencies"""
        self.log("Step 1: Installing LangGraph dependencies...")
        
        try:
            # Install LangGraph dependencies
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "langgraph", "langchain-openai", "langchain-anthropic", 
                "langchain-google-genai", "langchain-core", "langchain-community"
            ], check=True)
            
            self.log("Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install dependencies: {e}", "ERROR")
            return False
    
    def step2_update_main_app(self):
        """Step 2: Update main application to include LangGraph routes"""
        self.log("Step 2: Updating main application...")
        
        main_py = self.project_root / "app" / "main.py"
        
        # Read current content
        with open(main_py, 'r') as f:
            content = f.read()
        
        # Check if already updated
        if "langgraph_routes" in content:
            self.log("Main app already updated")
            return True
        
        # Add LangGraph import and router
        if "from app.api.routes import router" in content:
            content = content.replace(
                "from app.api.routes import router",
                "from app.api.routes import router\\nfrom app.api.langgraph_routes import router as langgraph_router"
            )
        
        if "app.include_router(router)" in content:
            content = content.replace(
                "app.include_router(router)",
                "app.include_router(router)\\napp.include_router(langgraph_router)"
            )
        
        # Write updated content
        with open(main_py, 'w') as f:
            f.write(content)
        
        self.log("Main application updated successfully")
        return True
    
    def step3_test_langgraph_service(self):
        """Step 3: Test LangGraph service initialization"""
        self.log("Step 3: Testing LangGraph service...")
        
        try:
            # Test basic import
            sys.path.insert(0, str(self.project_root))
            
            # Test mock service first
            subprocess.run([
                sys.executable, "test_langgraph_simplification.py"
            ], check=True, cwd=self.project_root)
            
            self.log("LangGraph service test passed")
            return True
            
        except Exception as e:
            self.log(f"LangGraph service test failed: {e}", "ERROR")
            return False
    
    def step4_run_validation_tests(self):
        """Step 4: Run comprehensive validation tests"""
        self.log("Step 4: Running validation tests...")
        
        try:
            # Run existing tests to ensure no regression
            subprocess.run([
                sys.executable, "-m", "pytest", "tests/", "-v"
            ], check=True, cwd=self.project_root)
            
            self.log("Validation tests passed")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Validation tests failed: {e}", "ERROR")
            return False
    
    def generate_migration_report(self):
        """Generate migration report"""
        self.log("Generating migration report...")
        
        # Count lines of code before/after
        legacy_lines = self.count_lines_in_directory(self.legacy_dir)
        current_lines = self.count_lines_in_directory(self.services_dir, exclude_dirs=["legacy"])
        
        report = f"""
# LangGraph Migration Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Code Reduction Analysis
- Legacy Implementation: {legacy_lines} lines
- LangGraph Implementation: {current_lines} lines
- Reduction: {legacy_lines - current_lines} lines ({((legacy_lines - current_lines) / legacy_lines * 100):.1f}%)

## Migration Status
- [x] Dependencies installed
- [x] Main application updated
- [x] LangGraph service tested
- [x] Validation tests passed

## Files Modified
- app/main.py (updated imports)
- app/services/langgraph_service.py (new)
- app/api/langgraph_routes.py (new)

## Files Backed Up
- All legacy services moved to app/services/legacy/
- Full backup created in migration_backup/

## Next Steps
1. Test new API endpoints
2. Migrate remaining features
3. Update documentation
4. Remove legacy code (when confident)
"""
        
        with open(self.project_root / "MIGRATION_REPORT.md", "w") as f:
            f.write(report)
        
        self.log("Migration report generated")
    
    def count_lines_in_directory(self, directory: Path, exclude_dirs: list = None) -> int:
        """Count lines of Python code in directory"""
        if not directory.exists():
            return 0
        
        exclude_dirs = exclude_dirs or []
        total_lines = 0
        
        for py_file in directory.rglob("*.py"):
            if any(exclude_dir in str(py_file) for exclude_dir in exclude_dirs):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    total_lines += len(f.readlines())
            except Exception:
                continue
        
        return total_lines
    
    def rollback_migration(self):
        """Rollback migration if needed"""
        self.log("Rolling back migration...")
        
        if not self.backup_dir.exists():
            self.log("No backup found for rollback", "ERROR")
            return False
        
        # Restore backed up files
        for item in self.backup_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(self.backup_dir)
                target_path = self.project_root / relative_path
                
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_path)
        
        self.log("Migration rolled back successfully")
        return True
    
    def run_full_migration(self):
        """Run complete migration process"""
        self.log("Starting full LangGraph migration...")
        
        # Create backup first
        self.create_backup()
        
        # Run all steps
        steps = [
            ("Installing dependencies", self.step1_install_dependencies),
            ("Updating main application", self.step2_update_main_app),
            ("Testing LangGraph service", self.step3_test_langgraph_service),
            ("Running validation tests", self.step4_run_validation_tests),
        ]
        
        for step_name, step_func in steps:
            self.log(f"Running: {step_name}")
            
            if not step_func():
                self.log(f"Migration failed at: {step_name}", "ERROR")
                self.log("Consider running rollback with --rollback flag", "ERROR")
                return False
        
        # Generate report
        self.generate_migration_report()
        
        self.log("Migration completed successfully! 🎉")
        self.log("Check MIGRATION_REPORT.md for details")
        return True

def main():
    parser = argparse.ArgumentParser(description="LangGraph Migration Tool")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], help="Run specific migration step")
    parser.add_argument("--full", action="store_true", help="Run complete migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration")
    
    args = parser.parse_args()
    
    migrator = LangGraphMigrator()
    
    if args.rollback:
        migrator.rollback_migration()
    elif args.full:
        migrator.run_full_migration()
    elif args.step:
        migrator.create_backup()
        
        step_functions = {
            1: migrator.step1_install_dependencies,
            2: migrator.step2_update_main_app,
            3: migrator.step3_test_langgraph_service,
            4: migrator.step4_run_validation_tests,
        }
        
        if step_functions[args.step]():
            print(f"Step {args.step} completed successfully")
        else:
            print(f"Step {args.step} failed")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 