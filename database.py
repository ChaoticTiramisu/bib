from sqlalchemy import String, Integer, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, mapped_column
from sqlalchemy_utils import database_exists, create_database

engine = create_engine("sqlite:///instance/bib.db", echo=True)

if not database_exists("sqlite:///instance/bib.db"):
    create_database(engine.url)

Base = declarative_base()

class Ontlener(Base):
    __tablename__ = "Ontlener"

    lln_id = mapped_column(Integer, primary_key=True, autoincrement=True)
    lln_naam = mapped_column(String)
    lln_achternaam = mapped_column(String)
    lln_geboortedtm = mapped_column(String)
    lln_tel_nr = mapped_column(Integer)
   
    login_id = mapped_column(Integer, ForeignKey('Login.lln_id'), unique=True)
    login = relationship("Login", back_populates="ontlener", foreign_keys=[login_id])


class Bibliothecaris(Base):
    __tablename__ = "Bibliothecaris"

    biblio_bib_id = mapped_column(Integer, primary_key=True, autoincrement=True)
    biblio_naam = mapped_column(String)
    biblio_achternaam = mapped_column(String)
    biblio_email = mapped_column(String)
    biblio_bib_recht = mapped_column(String)
    biblio_tel_nr = mapped_column(Integer)
    
    login_id = mapped_column(Integer, ForeignKey('Login.biblio_bib_id'), unique=True)
    login = relationship("Login", back_populates="bibliothecaris", foreign_keys=[login_id])

class Boeken(Base):
    __tablename__ = "Boeken"

    bkn_ISBN = mapped_column(String, primary_key=True)
    bkn_genre = mapped_column(String)
    bkn_thema = mapped_column(String)
    bkn_auteur = mapped_column(String)

class Login(Base):
    __tablename__ = "Login"
    
    login_id = mapped_column(Integer, primary_key=True, autoincrement=True)
    lln_id = mapped_column(Integer, ForeignKey("Ontlener.lln_id"), remote_side=[Ontlener.lln_id])
    biblio_bib_id = mapped_column(Integer, ForeignKey("Bibliothecaris.biblio_bib_id"), remote_side=[Bibliothecaris.biblio_bib_id])
    user_email = mapped_column(String)
    user_paswoord = mapped_column(String)

    ontlener = relationship("Ontlener", back_populates="login", foreign_keys=[lln_id])
    bibliothecaris = relationship("Bibliothecaris", back_populates="login", foreign_keys=[biblio_bib_id])

Base.metadata.create_all(bind=engine)
