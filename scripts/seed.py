"""Carga datos de ejemplo: un usuario demo y varios libros.   Uso: python -m scripts.seed
Primero aplica las migraciones:  alembic upgrade head"""
from sgb.database import SessionLocal
from sgb.models import Autor, Categoria, Libro, Usuario
from sgb.repositories import LibroRepository, UsuarioRepository
from sgb.security import hash_password

DEMO = {"nombre": "Usuario Demo", "identificacion": "0000", "email": "demo@sgb.local", "password": "Demo12345"}
LIBROS = [
    ("Cien años de soledad", "Gabriel García Márquez", "Novela", "Sudamericana", 1967, 3),
    ("El amor en los tiempos del cólera", "Gabriel García Márquez", "Novela", "Oveja Negra", 1985, 2),
    ("Clean Code", "Robert C. Martin", "Software", "Prentice Hall", 2008, 4),
    ("Introduction to Algorithms", "Thomas H. Cormen", "Software", "MIT Press", 2009, 1),
    ("Don Quijote de la Mancha", "Miguel de Cervantes", "Clásico", "Francisco de Robles", 1605, 2),
    ("Sapiens", "Yuval Noah Harari", "Historia", "Debate", 2011, 3),
]

with SessionLocal() as s:
    if not s.query(Usuario).filter_by(email=DEMO["email"]).first():
        UsuarioRepository(s).crear(Usuario(nombre=DEMO["nombre"], identificacion=DEMO["identificacion"], email=DEMO["email"],
                                           password_hash=hash_password(DEMO["password"])))
        print(f"Usuario demo: {DEMO['email']} / {DEMO['password']}")
    repo = LibroRepository(s)
    for titulo, autor, cat, editorial, anio, n in LIBROS:
        if s.query(Libro).filter_by(titulo=titulo).first():
            continue
        a = s.query(Autor).filter_by(nombre=autor).first() or Autor(nombre=autor)
        c = s.query(Categoria).filter_by(nombre=cat).first() or Categoria(nombre=cat)
        s.add_all([a, c]); s.flush()
        repo.crear(Libro(titulo=titulo, editorial=editorial, anio=anio, ejemplares_totales=n, ejemplares_disponibles=n,
                         autor_id=a.id, categoria_id=c.id))
    print("Libros en catálogo:", s.query(Libro).count())
