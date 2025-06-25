import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from crud import product as crud_product
from schemas import product as schemas_product
from models.product import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

def test_create_product(db_session):
    product_in = schemas_product.ProductCreate(
        product_url="http://example.com/product",
        name="Test Product",
        sku="TEST-123",
        price=99.99,
        currency="USD",
        all_image_urls=["http://example.com/image1.jpg"],
        available_sizes=["S", "M"],
    )
    db_product = crud_product.create_product(db_session, product_in)
    assert db_product.name == "Test Product"
    assert db_product.sku == "TEST-123"
    assert len(db_product.images) == 1
    assert len(db_product.sizes) == 2

def test_get_product_by_url(db_session):
    product_in = schemas_product.ProductCreate(
        product_url="http://example.com/product2",
        name="Test Product 2",
        sku="TEST-456",
    )
    crud_product.create_product(db_session, product_in)
    db_product = crud_product.get_product_by_url(db_session, "http://example.com/product2")
    assert db_product is not None
    assert db_product.name == "Test Product 2"
