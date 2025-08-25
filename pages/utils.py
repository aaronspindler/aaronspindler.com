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