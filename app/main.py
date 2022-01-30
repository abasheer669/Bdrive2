from os import getcwd, remove
import os
from fastapi.responses import FileResponse,JSONResponse
from pathlib import Path
from typing import Optional
from typing import List
from datetime import datetime
from fastapi import FastAPI, File, UploadFile,Depends,HTTPException,status,Request,Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from .schemas import Item,User, UserCreate
from . import schemas, database, models, token,hashing, forms

from .database import SessionLocal, engine,get_db
from sqlalchemy.orm import Session
from .import crud,models,schemas,token

from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse


app = FastAPI()

BASE_PATH = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))

models.Base.metadata.create_all(bind=engine)


#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/register",response_model=User)
async def create_user(request:Request):
    return templates.TemplateResponse('register.html', context={'request': request})


@app.post("/register",response_model=User)
async def create_user(request:Request,db: Session = Depends(get_db)):

    form = forms.RegistrationForm(request)
    await form.load_data()
        
    if await form.is_valid():
        user = UserCreate(username=form.username, email=form.email, password=form.password)

    db_email = crud.get_user_by_email(db, email=user.email)
    db_username=crud.get_user(db, username=user.username)

    if db_email :
        raise HTTPException(status_code=400, detail="Email already registered")
    if db_username :
        raise HTTPException(status_code=400, detail="username already registered")

    crud.create_user(db=db, user=user)
    return templates.TemplateResponse("register.html", form.__dict__)


    
# @app.get("/uploadfiles",status_code=200)
# def upload(request: Request, db: Session = Depends(get_db)):
#     token = request.cookies.get("access_token")
#     if not token:
#         print("Login is must!") 
#         response = RedirectResponse('/login', status_code=303)
#         return response
#         #templates.TemplateResponse("login.html",{"request": request})
#     return templates.TemplateResponse("uploadfiles.html", {"request": request})



#,response_model=schemas.TokenData)
def create_upload_files(request: Request,myfiles: List[UploadFile]= File (...),db: Session = Depends(get_db)):
    #print(user.username)
    access_token = request.cookies.get("access_token")
    #print("token: ", access_token)
    scheme, param = get_authorization_scheme_param(access_token)  # scheme will hold "Bearer" and param will hold actual token value
    user: User = token.get_current_user_from_token(token=param, db=db)
    if not user:
         return templates.TemplateResponse("login.html",{"request": request})

    current_user = db.query(models.User).filter(models.User.email ==user.email).first()
    #print(user.username)
    existing_files = db.query(models.File).filter(models.File.user_id ==user.id)
    
    for file in myfiles:
        #print(file.filename)
        if file  in existing_files:
            print("file.filename alread exist!")
            continue

        file_location = os.path.join(f'D:/sem 8/Hackathon/app/static/{file.filename}')
        
        with open(file_location, "wb+") as buffer:
            content = file.file.read()
            buffer.write(content)
            buffer.close()
        print("copied")
        db_file = models.File(filename=file.filename,date_uploaded=str(datetime.utcnow()),user_id=current_user.id)
        db.add(db_file)
    db.commit()
    #print("uploaded")
    #return templates.TemplateResponse("files.html",{"request": request})
    

@app.get("/files",status_code=200)
def get_all(request: Request, db: Session = Depends(get_db)):
    data=[]
    access_token = request.cookies.get("access_token")
    #print("token: ", token)
    scheme, param = get_authorization_scheme_param(access_token)  # scheme will hold "Bearer" and param will hold actual token value
    current_user: User = token.get_current_user_from_token(token=param, db=db)
    if not current_user:
         return templates.TemplateResponse("login.html",{"request": request})

    user = db.query(models.User).filter(models.User.email ==current_user.email).first()
    files = db.query(models.File).filter(models.File.user_id ==user.id)

    for file in files:
        data.append(file)
    #print(data)

        #templates.TemplateResponse("login.html",{"request": request})
    return templates.TemplateResponse("files.html", {"request": request,"data":data})


@app.post("/files",status_code=200)
def get_all(request:Request,db: Session = Depends(get_db),myfiles: List[UploadFile]= File (...)):
    #path='D:/sem 8/Hackathon/app/static/'
    data=[]
    
    access_token = request.cookies.get("access_token")
    #print("token: ", token)
    scheme, param = get_authorization_scheme_param(access_token)  # scheme will hold "Bearer" and param will hold actual token value
    current_user: User = token.get_current_user_from_token(token=param, db=db)
    if not current_user:
         return templates.TemplateResponse("login.html",{"request": request})
    print( "req")
    print( request)
    create_upload_files(request,myfiles,db)

    user = db.query(models.User).filter(models.User.email ==current_user.email).first()
    files = db.query(models.File).filter(models.File.user_id ==user.id)


    for file in files:
        data.append(file)
    print(data)
    

    return templates.TemplateResponse("files.html", {"request":Request,"data":data})
    #FileResponse(path + name_file, media_type='application/octet-stream', filename=name_file)


@app.get("/download/{name_file}",status_code=200)
def download_file(request:Request,name_file: str,db: Session = Depends(get_db)):

    access_token = request.cookies.get("access_token")
    print("token: ", token)
    scheme, param = get_authorization_scheme_param(access_token)  # scheme will hold "Bearer" and param will hold actual token value
    current_user: User = token.get_current_user_from_token(token=param, db=db)
    if not current_user:
         return templates.TemplateResponse("login.html",{"request": request})

    path='D:/sem 8/Hackathon/app/static/'
    user = db.query(models.User).filter(models.User.email ==current_user.email).first()
    
    file = db.query(models.File).filter(models.File.user_id ==user.id).first()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="File not found")
    return FileResponse(path + name_file, media_type='application/octet-stream', filename=name_file)

@app.delete("/delete/{name_file}")
def delete_file(request:Request,name_file: str,db: Session = Depends(get_db),):
    
    access_token = request.cookies.get("access_token")
    print("token: ", token)
    scheme, param = get_authorization_scheme_param(access_token)  # scheme will hold "Bearer" and param will hold actual token value
    current_user: User = token.get_current_user_from_token(token=param, db=db)
    if not current_user:
         return templates.TemplateResponse("login.html",{"request": request})


    path='D:/sem 8/Hackathon/app/static/'
    user = db.query(models.User).filter(models.User.email ==current_user.email).first()
    try:
        file= db.query(models.File).filter(models.File.user_id ==user.id)
        file.delete(synchronize_session=False)
        db.commit()
        remove( path + name_file)

        return JSONResponse(content={
            "removed": True
            }, status_code=200)   
    except FileNotFoundError:
        return JSONResponse(content={
            "removed": False,
            "error_message": "File not found"
        }, status_code=404)


@app.get("/login",response_model=User)
def login(request:Request):
    return templates.TemplateResponse('login.html', context={'request': request})

@app.post('/login',response_model=User)
async def login(request:Request, db: Session = Depends(database.get_db)):

    form = forms.LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            response = templates.TemplateResponse("login.html", form.__dict__)
            token.login_for_access_token(response=response, form_data=form, db=db)
            return response
        except HTTPException:
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Incorrect Email or Password")
   
    return templates.TemplateResponse("login.html", form.__dict__)
    
    
    