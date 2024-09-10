# pip install requests bs4 lxml tqdm colorama

import getpass
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from colorama import Fore
from colorama.initialise import init
from tqdm import tqdm


init()

headers = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 "
                  "YaBrowser/22.11.3.838 Yowser/2.5 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.9"
}


def get_html(url: str) -> (str, bool):

    try:
        rs = requests.get(url=url, headers=headers, timeout=5)
        return rs.text if rs.status_code == 200 else False
    except Exception:
        return False


def get_track(txt: str) -> list:

    temp = []
    soup = BeautifulSoup(txt, "lxml")
    all_muz = soup.find_all('div', class_="track__info")
    for muz in all_muz:
        title = muz.find('div', class_="track__title").text.strip()
        link = muz.find('div', class_="track__info-r").find('a').get('href')
        artist_song = soup.find('div', class_="track__desc").text.strip()
        duration = soup.find('div', class_="track__time").find('div', class_='track__fulltime').text.strip()
        time_track = f'{int(duration.split(":")[0]) * 60 + int(duration.split(":")[1])}'
        temp.append(f'#EXTINF:{time_track}, group-title="{artist_song}", {title}\n{link}\n')
        print(f'{artist_song} - {title}\n{link}\n')
    return temp


def get_links(path: Path, iter_num: int, iter_link: str) -> (list, bool):

    temp = []

    if iter_num == 0:
        if txt := get_html(f'{iter_link}0'):
            temp.extend(get_track(txt))
    else:
        for i in range(0, iter_num+1, 48):
            link = f'{iter_link}{i}'
            if txt := get_html(link):
                temp.extend(get_track(txt))

    if temp:
        path.mkdir(exist_ok=True)
        with open(path / f'{path.name}_web.m3u', mode='w', encoding='utf-8') as file:
            file.write("#EXTM3U\n")
            for item in temp:
                file.write(item)
        return [x.split("\n")[1].strip() for x in temp], len(temp)
    return False


def get_pagination_artist(url: str) -> tuple:

    if txt := get_html(url):
        soup = BeautifulSoup(txt, "lxml")
        artist = ""
        try:
            artist = soup.find('ul', class_="breadcrumb").find_all('li')[-1].text.strip()
            section = soup.find('section', class_="pagination").find('ul', class_="pagination__list").find_all('li')[-1].\
                find('a').get('href')
            return urljoin(url, section), artist
        except Exception:
            return False, artist
    return False, False


def track_download(url, path) -> bool:

    filename = ""
    try:

        rs = requests.get(url=url, headers=headers, stream=True)
        if rs.status_code == 200:
            file_size = int(rs.headers.get("Content-Length", 0))
            filename = Path(url).name
            progress = tqdm(rs.iter_content(1024), f"{Fore.GREEN}Downloading: {Fore.RESET}"
                                                   f"{filename}", total=file_size, unit="B",
                            unit_scale=True, unit_divisor=1024)
            with open(path / filename, "wb") as f:
                for data in progress.iterable:
                    f.write(data)
                    progress.update(len(data))
        return False
    except KeyboardInterrupt:
        (path / filename).unlink()
        print(f"\n{Fore.GREEN}До свидания: {Fore.RESET}{getpass.getuser()}\n")
        sys.exit(0)
    except Exception:
        print(f"Не удалось загрузить: {url}")
        return False


def main():
    """
    Получение ссылки на страницу для загрузки.
    Запрос у пользователя дополнительных действий.
    Запуск функций для получения плейлистов и загрузки треков.
    """
    try:
        link = input("\nВведите ссылку на альбом исполнителя (ru.hitmotop.com): ")
        if not link.startswith("http"):
            print("\n[!] Введите ссылку")
            main()
            return
        pag_link, artist = get_pagination_artist(link)
        print("")
        if not pag_link and not artist:
            raise KeyboardInterrupt
        path = Path.cwd() / artist
        if (path / f'{path.name}_web.m3u').exists():
            print(f'{Fore.RED}Плейлист: "{path.name}_web.m3u" существует. И будет перезаписан.{Fore.RESET}')
            (path / f'{path.name}_web.m3u').unlink()
        if pag_link:
            iter_num = int(pag_link.split("/")[-1])
            iter_link = f'{"/".join(pag_link.split("/")[:-1])}/'
            links, count = get_links(path, iter_num, iter_link)
        else:
            links, count = get_links(path, 0, f'{link}/start/')

        if links:
            ch = input(f"\n{Fore.YELLOW}Плейлист сохранен. Получено ссылок: {Fore.RESET}{count}. "
                       f"{Fore.YELLOW}Загрузить треки? y/n: ")
            if ch.lower() in ['y', 'yes']:
                path.mkdir(exist_ok=True)
                count_track = int(input("Введите количество треков которые хотите загрузить: "))
                for url in links[:count_track]:
                    if (path / Path(url).name).exists():
                        print(f"{Fore.YELLOW}Пропуск: {Fore.RESET}{Path(url).name} | {Fore.YELLOW}Существует")
                        continue
                    track_download(url, path)
            else:
                raise KeyboardInterrupt
        else:
            print(f"{Fore.RED}Не удалось получить ссылки")
            raise KeyboardInterrupt
        print(f"\n{Fore.GREEN}Все файлы загружены в папку: {Fore.RESET}{path}\n")

    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}До свидания: {Fore.RESET}{getpass.getuser()}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()