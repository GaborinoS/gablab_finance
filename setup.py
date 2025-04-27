import os
import sys
import shutil

# Make sure we can import from the app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, PortfolioData, CostIncomeEntry

def setup_directories():
    """Setup necessary directories for the application"""
    print("Setting up directories...")
    
    # Ensure data directory exists
    data_dir = os.path.join('app', 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created directory: {data_dir}")
    
    # Ensure migrations directory exists
    migrations_dir = 'migrations'
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)
        print(f"Created directory: {migrations_dir}")
    
    # Create user-specific data directories
    users_data_dir = os.path.join('app', 'data', 'users')
    if not os.path.exists(users_data_dir):
        os.makedirs(users_data_dir)
        print(f"Created directory: {users_data_dir}")
    
    print("Directories setup completed")

def setup_database():
    """Initialize and setup the database"""
    print("Setting up database...")
    
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created")
    
    print("Database setup completed")

def migrate_data():
    """Run the data migration script"""
    print("Migrating existing data...")
    
    try:
        # Run the migration script
        from migrations.initial_setup import main
        main()
        print("Data migration completed")
    except Exception as e:
        print(f"Error during data migration: {e}")

def main():
    """Main function to run all setup steps"""
    print("Starting Gab-Lab Finance setup...")
    
    # Setup directories
    setup_directories()
    
    # Setup database
    setup_database()
    
    # Migrate data
    migrate_data()
    
    print("\nSetup completed successfully!")
    print("\nDefault users created:")
    print("- Admin: username=admin, password=adminpassword")
    print("- User 1: username=user1, password=password1")
    print("- User 2: username=user2, password=password2")
    print("\nYou can now run the application with 'python run.py'")

if __name__ == "__main__":
    main()