from fastapi import FastAPI, Depends, HTTPException
from pydantic import computed_field
from typing import Optional, List
from sqlmodel import Field, SQLModel, Session, create_engine, select

# --- Database Setup ---
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

# --- Models ---
class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    item_type: str  # "Book" or "Project"
    total_chapters: int
    current_chap: int = Field(default=0)

    @computed_field
    @property
    def status(self) -> str:
        if self.current_chap == 0:
            return "Not Started"
        if self.current_chap >= self.total_chapters:
            return "Completed"
        return "In Progress"

    @computed_field
    @property
    def percentage(self) -> float:
        if self.total_chapters == 0:
            return 0.0
        return round((self.current_chap / self.total_chapters) * 100, 2)


class Chapter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="item.id")
    title: Optional[str] = Field(default=None)
    chap_num: int
    status: str = Field(default="Not Started")  # "Not Started", "in_progress", "completed"


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(title="Complete Progress Tracker API")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

def get_sessions():
    with Session(engine) as session:
        yield session   

@app.get("/")
def home():
    return {"Message": "Hello There !!! Welcome to the Complete Status Tracker API"}


# ==========================================
# 1. CREATE OPERATIONS (C)
# ==========================================
@app.post("/items/", response_model=Item, status_code=201)
def create_item(item: Item, session: Session = Depends(get_sessions)):
    """Create a new item and auto-generate its child chapters."""
    session.add(item)
    session.commit()
    session.refresh(item)

    # Auto-generate child chapters based on total_chapters
    for i in range(1, item.total_chapters + 1):
        chapter = Chapter(item_id=item.id, chap_num=i, title=f"Chapter - {i}")
        session.add(chapter)
    session.commit()

    return item


# ==========================================
# 2. READ OPERATIONS (R)
# ==========================================
@app.get("/items/", response_model=List[Item])
def get_all_items(session: Session = Depends(get_sessions)):
    """Retrieve all items from the database."""
    return session.exec(select(Item)).all()


@app.get("/items/{item_id}")
def get_item_with_chapters(item_id: int, session: Session = Depends(get_sessions)):
    """Retrieve a specific item along with all its child chapters."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")

    chapters = session.exec(select(Chapter).where(Chapter.item_id == item_id)).all()
    return {
        "item": item,
        "chapters": chapters
    }


# ==========================================
# 3. UPDATE OPERATIONS (U)
# ==========================================

# --- Update Item (PATCH) ---
@app.patch("/items/{item_id}", response_model=Item)
def update_item(
    item_id: int, 
    title: Optional[str] = None, 
    description: Optional[str] = None, 
    item_type: Optional[str] = None,
    total_chapters: Optional[int] = None,
    current_chap: Optional[int] = None,
    session: Session = Depends(get_sessions)
):
    """Partially update an item's details or progress."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if title is not None:
        item.title = title
    if description is not None:
        item.description = description
    if item_type is not None:
        item.item_type = item_type
    if total_chapters is not None:
        item.total_chapters = total_chapters
    if current_chap is not None:
        if current_chap > item.total_chapters:
            raise HTTPException(status_code=400, detail="current_chap cannot exceed total_chapters")
        item.current_chap = current_chap
        
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


# --- Full Chapter Update (PUT) ---
@app.put("/items/{item_id}/chapters/{chap_num}", response_model=Chapter)
def update_entire_chapter(
    item_id: int, 
    chap_num: int, 
    updated_chapter: Chapter, 
    session: Session = Depends(get_sessions)
):
    """Fully replace all fields of a specific chapter."""
    statement = select(Chapter).where(
        Chapter.item_id == item_id, 
        Chapter.chap_num == chap_num
    )
    chapter = session.exec(statement).first()
    
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found for this item!")

    chapter.chap_num = updated_chapter.chap_num
    chapter.title = updated_chapter.title
    chapter.status = updated_chapter.status

    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


# --- Partial Chapter Status Update (PATCH) ---
@app.patch("/items/{item_id}/chapters/{chap_num}", response_model=Chapter)
def update_chapter_status(
    item_id: int, 
    chap_num: int, 
    new_status: str, 
    session: Session = Depends(get_sessions)
):
    """Partially update just a chapter's status."""
    allowed_statuses = ["Not Started", "in_progress", "completed"]
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from {allowed_statuses}")
    
    statement = select(Chapter).where(
        Chapter.item_id == item_id, 
        Chapter.chap_num == chap_num
    )
    chapter = session.exec(statement).first()
    
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found for this item")
    
    chapter.status = new_status
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


# ==========================================
# 4. DELETE OPERATIONS (D)
# ==========================================
@app.delete("/items/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_sessions)):
    """Delete an item and cascade delete all its child chapters to prevent orphans."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # 1. Delete associated child chapters first
    chapters = session.exec(select(Chapter).where(Chapter.item_id == item_id)).all()
    for chapter in chapters:
        session.delete(chapter)
    
    # 2. Delete the parent item
    session.delete(item)
    session.commit()
    
    return {"message": f"Item '{item.title}' and all its {len(chapters)} chapters successfully deleted."}