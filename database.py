from sqlalchemy import String,Integer,Boolean,ForeignKey,create_engine
from sqlalchemy.orm import DeclarativeBase,Mapped,sessionmaker,mapped_column,relationship


engine = create_engine("sqlite:///databases/Bib.db", echo=True)

class Base(DeclarativeBase):
    pass

class Bibliothecaris(Base):
    __tablename__ = "Bibliothecaris"

    biblio_bib_id:Mapped[int] = mapped_column(primary_key = True)
    biblio_naam:Mapped[str] = mapped_column()
    biblio_achternaam:Mapped[str] = mapped_column()
    biblio_email:Mapped[str] = mapped_column()
    biblio_bib_recht:Mapped[str] = mapped_column()
    biblio_tel_nr:Mapped[int] = mapped_column()

class Ontlener(Base):
    __tablename__ = "Ontlener"

    lln_id:Mapped[int] = mapped_column(primary_key=True)
    lln_naam:Mapped[str] = mapped_column()
    lln_achternaam:Mapped[str] = mapped_column()
    lln_email:Mapped[str] = mapped_column()
    lln_geboortedtm:Mapped[str] = mapped_column()
    lln_tel_nr:Mapped[int] = mapped_column()

class Boeken(Base):
    __tablename__="Boeken"

    bkn_genre:Mapped[str] = mapped_column()
    bkn_thema:Mapped[str] = mapped_column()
    bkn_auteur:Mapped[str] = mapped_column()
    


Base.metadata.create_all(bind=engine)

Session = sessionmaker(bind=engine)
session = Session()

def bibliothecaris(Bib_id,Naam,Achternaam,Email,Bib_recht,Tel_nr_bib):

    persoon = Bibliothecaris(biblio_bib_id = Bib_id,
                             biblio_naam = Naam,
                             biblio_achternaam = Achternaam,
                             biblio_email = Email,
                             biblio_bib_recht =Bib_recht,
                             biblio_tel_nr = Tel_nr_bib)
    session.add(persoon)
    session.commit()