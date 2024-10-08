import datetime
import os
from django.conf import settings
from django.template.loader import render_to_string

def get_blog_from_template_name(template_name, load_content=True):
    entry_number = template_name.split("_")[0]
    blog_title = template_name.replace("_", " ").title()
    blog_content = render_to_string(f"blog/{template_name}.html") if load_content else ""
    
    # These were removed because they don't actually work on the deployed server
    # blog_post_path = os.path.join(settings.BASE_DIR, 'templates', 'blog', f'{template_name}.html')
    # created_timestamp = os.path.getctime(blog_post_path)
    # created_at = str(datetime.datetime.fromtimestamp(created_timestamp).strftime('%Y-%m-%d'))
    # updated_timestamp = os.path.getmtime(blog_post_path)
    # updated_at = str(datetime.datetime.fromtimestamp(updated_timestamp).strftime('%Y-%m-%d'))
    
    return {
        "entry_number": entry_number,
        "template_name": template_name,
        "blog_title": blog_title,
        "blog_content": blog_content,
        "github_link": f"https://github.com/aaronspindler/aaronspindler.com/commits/main/templates/blog/{template_name}.html",
        
        # "created_timestamp": created_timestamp,
        # "updated_timestamp": updated_timestamp,
        # "created_at": created_at,
        # "updated_at": updated_at,
    }

def get_books():
    books = []
    books.append({
        "name": "Dark Mirror",
        "cover_image": "images/dark-mirror.jpg",
    })
    books.append({
        "name": "The Little Book of Market Wizards",
        "cover_image": "images/the-little-book-of-market-wizards.jpg",
    })
    books.append({
        "name": "Long Range Shooting Handbook",
        "cover_image": "images/long-range-handbook.jpg",
    })
    books.append({
        "name": "The Inevitable",
        "cover_image": "images/the_inevitable.jpg",
    })
    books.append({
        "name": "Data for the People",
        "cover_image": "images/data-for-the-people.jpg",
    })
    books.append({
        "name": "Django 3 By Example",
        "cover_image": "images/django-3-by-example.png",
    })
    books.append({
        "name": "Permanent Record",
        "cover_image": "images/permanent-record.jpg",
        "favourite_quote": "Credit cards are like little personal trackers, tracking your every move"
    })
    books.append({
        "name": "Principles",
        "cover_image": "images/principles.jpg",
    })
    books.append({
        "name": "Django For Professionals",
        "cover_image": "images/djangoforprofessionals.jpg",
        "favourite_quote": "Searching and sorting can be very complex, but it doesn't have to be!"
    })
    books.append({
        "name": "Cracking the Coding Interview",
        "cover_image": "images/crackingthecodinginterview.jpg",
        "favourite_quote": "This is going to be a hard one"
    })
    books.append({
        "name": "Assume the Worst",
        "cover_image": "images/assumetheworst.jpg",
        "favourite_quote": "You've probably never been told this, but you are going to fail. Over and over again!"
    })
    books.append({
        "name": "Six Not So Easy Pieces",
        "cover_image": "images/6notsoeasypieces.jpg",
    })
    books.append({
        "name": "Six Easy Pieces",
        "cover_image": "images/6easypieces.jpg",
    })
    books.append({
        "name": "Blockchain",
        "cover_image": "images/blockchain-the-next-everything.jpg",
    })
    books.append({
        "name": "Make",
        "cover_image": "images/make.jpg",
    })
    books.append({
        "name": "The Healthy Programmer",
        "cover_image": "images/healthyprogrammer.jpeg",
    })
    books.sort(key=lambda x: x['name'], reverse=False)

    return books