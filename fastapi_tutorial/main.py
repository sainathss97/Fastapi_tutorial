from fastapi import FastAPI,Depends,HTTPException
from pydantic import BaseModel, computed_field
from typing import Optional, List
from sqlmodel import Field,SQLModel,Session,create_engine,select

# Configure SQLite as the application's persistent store. The connection option
# allows the same database connection to be used across FastAPI request threads.
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args= {"check_same_thread":False})

# Define the database tables and the computed progress values returned for items.

class Item(SQLModel,table=True):
    id:Optional[int] = Field(default=None, primary_key=True)
    title:str
    description:str
    item_type:str # opt1. Project,  opt2. Book
    total_chapters:int #
    current_chap:int #0-99

    # Derive a readable progress state from the item's current chapter count.
    @computed_field
    @property
    def status(self) -> str:
        if self.current_chap == 0:
            return "Not Started"
        if self.current_chap >= self.total_chapters:
            return "Completed"
        return "In Progress"


    # Report completion as a percentage, avoiding division by zero for empty items.
    @computed_field
    @property
    def percentage(self) -> float:
        if self.total_chapters ==0:
            return 0.0
        
        else:
            return round((self.current_chap/self.total_chapters)*100)
        

# Store each chapter separately and associate it with its parent item by foreign key.
class Chapter(SQLModel,table=True):
    id:Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key= "item.id")
    title:Optional[str] = Field(default=None)
    chap_num:int
    status:str = Field(default="Not Started")#In Progress, Completed, Not Started        

# Create all declared SQLModel tables if they do not already exist.
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Create the FastAPI application and initialize its database during startup.
app = FastAPI(title= "Progress Tracker - Day -2")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Provide one database session per request and close it after the request finishes.
def get_sessions():
    with Session(engine) as session:
        yield session   

# Return a simple greeting from the service's root endpoint.
@app.get("/")
def home():
    print(f"Hello There !!! welcome to Status Tracker ")
    return {"Message":f"Hello There !!! welcome to Status Tracker " }


# Save a new item, then create one initially unstarted chapter row for each chapter.
@app.post("/items/", response_model=Item,status_code=201)
def create_items(item:Item,session: Session= Depends(get_sessions)):
    session.add(item)
    session.commit()
    session.refresh(item)

    for i in range(1,item.total_chapters+1):
        chapter = Chapter(item_id=item.id, chap_num =i , title =f"Chapter - {i}")
        session.add(chapter)
    session.commit()

    return item

# Return every item currently stored in the database.
@app.get("/items/",response_model=List[Item])
def show_items(session: Session= Depends(get_sessions)):
    items = session.exec(select(Item)).all()
    return items

# Look up the item and prepare a response containing it and the chapter query results.
@app.get("/item/{item_id}")
def show_items_with_chaps(item_id: int,session: Session= Depends(get_sessions)):

    item = session.get(Item,item_id)
    if not item:
        raise HTTPException(status_code=404, detail =f"Cannot find {item}")

    chapters = session.exec(select(Chapter).where(Chapter.item_id == Item.id)).all()
    return {"item":item,
            "chapters":chapters}