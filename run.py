import sys
import os
from app import create_app, db

app = create_app()

# Handle command line arguments
if len(sys.argv) > 1:
    command = sys.argv[1]
    
    if command == "reset_db":
        with app.app_context():
            print("Dropping all database tables...")
            db.drop_all()
            print("Creating all database tables...")
            db.create_all()
            print("Database reset completed")
            
            # Run the migration script to populate the database
            try:
                from migrations.initial_setup import main
                main()
                print("Data migration completed")
            except Exception as e:
                print(f"Error during data migration: {e}")
        
        sys.exit(0)
    elif command == "setup":
        # Run the setup script
        import setup
        setup.main()
        sys.exit(0)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)