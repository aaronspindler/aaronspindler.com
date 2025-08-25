def get_books():
    books = []
    books.append({
        "name": "Dark Mirror",
        "author": "Barton Gellman",
        "cover_image": "images/dark-mirror.jpg",
    })
    books.append({
        "name": "The Little Book of Market Wizards",
        "author": "Jack D. Schwager",
        "cover_image": "images/the-little-book-of-market-wizards.jpg",
    })
    books.append({
        "name": "Long Range Shooting Handbook",
        "author": "Ryan M. Cleckner",
        "cover_image": "images/long-range-handbook.jpg",
    })
    books.append({
        "name": "The Inevitable",
        "author": "Kevin Kelly",
        "cover_image": "images/the_inevitable.jpg",
    })
    books.append({
        "name": "Data for the People",
        "author": "Andreas Weigend",
        "cover_image": "images/data-for-the-people.jpg",
    })
    books.append({
        "name": "Django 3 By Example",
        "author": "Antonio Mele",
        "cover_image": "images/django-3-by-example.png",
    })
    books.append({
        "name": "Permanent Record",
        "author": "Edward Snowden",
        "cover_image": "images/permanent-record.jpg",
        "favourite_quote": "Credit cards are like little personal trackers, tracking your every move"
    })
    books.append({
        "name": "Principles",
        "author": "Ray Dalio",
        "cover_image": "images/principles.jpg",
    })
    books.append({
        "name": "Django For Professionals",
        "author": "William S. Vincent",
        "cover_image": "images/djangoforprofessionals.jpg",
        "favourite_quote": "Searching and sorting can be very complex, but it doesn't have to be!"
    })
    books.append({
        "name": "Cracking the Coding Interview",
        "author": "Gayle Laakmann McDowell",
        "cover_image": "images/crackingthecodinginterview.jpg",
        "favourite_quote": "This is going to be a hard one"
    })
    books.append({
        "name": "Assume the Worst",
        "author": "Carl Hiaasen",
        "cover_image": "images/assumetheworst.jpg",
        "favourite_quote": "You've probably never been told this, but you are going to fail. Over and over again!"
    })
    books.append({
        "name": "Six Not So Easy Pieces",
        "author": "Richard P. Feynman",
        "cover_image": "images/6notsoeasypieces.jpg",
    })
    books.append({
        "name": "Six Easy Pieces",
        "author": "Richard P. Feynman",
        "cover_image": "images/6easypieces.jpg",
    })
    books.append({
        "name": "Blockchain",
        "author": "Stephen P. Williams",
        "cover_image": "images/blockchain-the-next-everything.jpg",
    })
    books.append({
        "name": "Make",
        "author": "Pieter Levels",
        "cover_image": "images/make.jpg",
    })
    books.append({
        "name": "The Healthy Programmer",
        "author": "Joe Kutner",
        "cover_image": "images/healthyprogrammer.jpeg",
    })
    books.sort(key=lambda x: x['name'], reverse=False)

    return books