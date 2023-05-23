Yatube Social Network
A social network for bloggers. It allows users to write posts and publish them in separate groups, subscribe to posts, add and delete entries, and comment on them. Users can also subscribe to their favorite bloggers.

Installation Instructions
- Clone the repository:

git clone git@github.com:aerobean/hw05_final.git
- Set up and activate a virtual environment:

For MacOS:
python3 -m venv venv
For Windows:
python -m venv venv
source venv/bin/activate
source venv/Scripts/activate
- Install the dependencies from the requirements.txt file:

pip install -r requirements.txt
- Apply the migrations:

python manage.py migrate
- In the directory containing the manage.py file, run the following command:

python manage.py runserver
