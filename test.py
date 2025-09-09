from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/")

def not_read_root():
    return({"message":"Hello World"})

def read_root():
    return({"message":"Hello NOT World"})

@app.get("/hello/{name}")
def say_hello(name: str):
    return {"greeting": f"Hello, {name}!"}

@app.post("/items/")
def create_item(item: Item):
    return {"message": f"Added {item.name} with price {item.price}"}

@app.get("/joke")
def get_joke():
    r = requests.get("https://official-joke-api.appspot.com/random_joke")
    return r.json()