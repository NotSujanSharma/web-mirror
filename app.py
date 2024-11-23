import requests
import re
import os


def get_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(e)
        return None

def save_file(url, path):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(path, 'wb') as f:
            f.write(response.content)
        return True
    except requests.exceptions.RequestException as e:
        print(e)
        return False


def make_directory(path):
    # Remove filename from path and ensure directory structure is correct
    path = os.path.dirname(path)
    base = "webpages/level1/level2/level3"  # Base directory
    full_path = os.path.join(base, path)  # Combine base with provided path

    try:
        # Create directories recursively; exist_ok=True handles pre-existing dirs
        os.makedirs(full_path, exist_ok=True)
        return full_path

    except OSError as e:
        print(f"Error creating directory: {e}")
        return None

def main():
    url = 'https://ableproadmin.com/dashboard/'

    content = get_content(url)

    if(content):

        #find all src attributes
        srcs = re.findall(r'src="([^"]+)"', content)

        for src in srcs:
            if src.startswith('/') or src.startswith('.'):
                local_path = make_directory(src)
                filename = os.path.basename(src)
                file_local_path = os.path.join(local_path, filename)
                file_src = url + src
                save_file(file_src, file_local_path)

        #find stylesheet href attributes
        stylesheets = re.findall(r'href="([^"]+\.css)"', content)
        for src in stylesheets:
            if src.startswith('/') or src.startswith('.'):
                local_path = make_directory(src)
                filename = os.path.basename(src)
                file_local_path = os.path.join(local_path, filename)
                file_src = url + src
                save_file(file_src, file_local_path)


    else:
        print('Failed to get content')



if __name__ == '__main__':
    main()