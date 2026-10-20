from fastapi import FastAPI
from pydantic import BaseModel, computed_field
from typing import Optional, List

app = FastAPI(title= "Day-1 Fast API Tutorial!!")

class Item(BaseModel):
    id:Optional[int] = None
    title:str
    description:str
    item_type:str # opt1. Project,  opt2. Book
    total_chapters:int #
    current_chap:int #0-99

    @computed_field
    @property
    def status(self) -> str:
        if self.current_chap == 0:
            return "Not Started"
        if self.current_chap >= self.total_chapters:
            return "Completed"
        return "In Progress"

fake_db =[]

@app.get("/")
def home():
    print(f"Hello There !!! welcome to day -1 ")
    return {"Message":f"Hello There !!! welcome to day -1 " }

@app.post("/items")
def post_update(item:Item):
    fake_db.append(item)
    return {"mesasge":f"{item} Created successfully!!",
            "data":f"{item}"}

@app.get("/show_items")
def show_items():
    if fake_db == []:
        return  {"Message": "Not Implemented no Post Requests"}
    return fake_db