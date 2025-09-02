@cli.command("create-admin")
def create_admin():
    admin_email = "admin@example.com"
    admin_password = "admin123"
    with Session(engine) as session:
        admin = session.query(Gebruiker).filter_by(email=admin_email).first()
        if not admin:
            admin = Gebruiker(
                naam="Admin",
                achternaam="User",
                email=admin_email,
                paswoord=admin_password,
                rol="admin",
                actief=True
            )
            session.add(admin)
            session.commit()
            print(f"Admin account created:\nEmail: {admin_email}\nPassword: {admin_password}")
        else:
            print(f"Admin account already exists:\nEmail: {admin_email}")

if __name__ == "__main__":
    cli()
