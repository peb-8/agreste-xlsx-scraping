Description : Scraping xlsx documents from the site "agreste.agriculture.gouv.fr"
Python version : 3.12
Usage : "python main.py"
Fonctionnalities:
    - Auto-discovering the files
    - Download only the new files
    - Streaming the files to lower memory usage
    - Able to use a certfile to secure the connection
    - Print time elapsed at the end
    - Business rules at the begining of the file for easy configuration
/!\ Set SSL=path/to/your/cert/file in production mode (to avoid man-in-the-middle attacks) /!\
