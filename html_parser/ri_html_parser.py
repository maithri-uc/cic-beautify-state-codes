import re
import roman
# import timeit
from bs4 import BeautifulSoup, Doctype
from os.path import exists
from datetime import datetime
from parser_base import ParserBase


class RIParseHtml(ParserBase):
    def __init__(self,input_file_name):
        super().__init__()
        self.html_file = input_file_name
        self.soup = None
        self.dictionary_to_store_class_name = {'h1': r'^Title \d+[A-Z]?(\.\d+)?', 'h4': 'Compiler’s Notes\.',
                                               'History': 'History of Section\.',
                                               'li': r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                               'h3': r'^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?|Chs. \d+  - \d+\.',
                                               'h2': r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                               'junk': 'Text', 'ol_of_i': '\([A-Z a-z]\)'}
        self.start_parse()

    def create_soup(self):
        with open(f'../transforms/ri/ocri/r{self.release_number}/raw/{self.html_file}') as file:
            file_name = file.read()
        self.soup = BeautifulSoup(file_name, 'html.parser')
        self.soup.contents[0].replace_with(Doctype("html"))
        self.soup.html.attrs['lang'] = 'en'
        file.close()

    def get_class_name(self):
        for key in self.dictionary_to_store_class_name:
            tag_class = self.soup.find(
                lambda tag: tag.name == 'p' and re.search(self.dictionary_to_store_class_name[key], tag.text.strip())and tag.attrs['class'][0] not in
                            self.dictionary_to_store_class_name.values())
            if tag_class:
                class_name = tag_class['class'][0]
                self.dictionary_to_store_class_name[key] = class_name
        print(self.dictionary_to_store_class_name)

    # def get_class_name(self):
    #     def class_name(tag):
    #         return tag.name=="p" and re.search(self.dictionary_to_store_class_name[key], tag.text.strip()) and \
    #                     tag.attrs['class'][0] not in self.dictionary_to_store_class_name.values()
    #
    #     for key in self.dictionary_to_store_class_name:
    #         # print(timeit.timeit(self.soup.find(class_name)))
    #         tag_class = self.soup.find(class_name)
    #         if tag_class:
    #             classname = tag_class['class'][0]
    #             self.dictionary_to_store_class_name[key] = classname
    #     print(self.dictionary_to_store_class_name)

    def remove_junk(self):
        for tag in self.soup.find_all("p", string=re.compile('Annotations|Text|History')):
            class_name = tag['class'][0]
            if class_name == self.dictionary_to_store_class_name['junk']:
                tag.decompose()

    def convert_to_header_and_assign_id(self):
        list_to_store_regex_for_h4 = ['Compiler’s Notes.', 'Compiler\'s Notes.', 'Cross References.',
                                      'Comparative Legislation.',
                                      'Collateral References.', 'NOTES TO DECISIONS',
                                      'Repealed Sections.', 'Effective Dates.', 'Law Reviews.', 'Rules of Court.',
                                      'OFFICIAL COMMENT', 'COMMISSIONER’S COMMENT','']
        count_for_duplicate = 0
        for tag in self.soup.find_all("p"):
            class_name = tag['class'][0]
            if class_name == self.dictionary_to_store_class_name['h1']:
                tag.name = "h1"
                if re.search("^Title \d+[A-Z]?(\.\d+)?", tag.text.strip()):
                    title_number = re.search("^Title (?P<title_number>\d+[A-Z]?(\.\d+)?)", tag.text.strip()).group(
                        'title_number').zfill(2)
                    tag.attrs['id'] = f"t{title_number}"
                else:
                    raise Exception('Title Not found...')
            elif class_name == self.dictionary_to_store_class_name['h2']:
                if re.search("^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?", tag.text.strip()):
                    tag.name = "h2"
                    chapter_number = re.search("^Chapters? (?P<chapter_number>\d+(\.\d+)?(\.\d+)?([A-Z])?)",
                                               tag.text.strip()).group('chapter_number').zfill(2)
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h1').attrs['id']}c{chapter_number}"
                    tag.attrs['class'] = "chapter"
                elif re.search("^Part (\d{1,2}|(IX|IV|V?I{0,3}))", tag.text.strip()):
                    tag.name = "h2"
                    part_number = re.search("^Part (?P<part_number>\d{1,2}|(IX|IV|V?I{0,3}))", tag.text.strip()).group(
                        'part_number').zfill(2)
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h2', class_='chapter').attrs['id']}p{part_number}"
                    tag['class'] = "part"
                elif re.search('^Subpart [A-Z0-9]', tag.text.strip()):
                    tag.name = "h2"
                    sub_part_number = re.search("^Subpart (?P<sub_part_number>[A-Z0-9])", tag.text.strip()).group(
                        'sub_part_number')
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h2', class_='part').attrs['id']}sp{sub_part_number}"
                elif re.search('^Article (\d+|(IX|IV|V?I{0,3}))', tag.text.strip()):
                    tag.name = "h2"
                    article_id = re.search('^Article (?P<article_id>(\d+|(IX|IV|V?I{0,3})))', tag.text.strip()).group(
                        'article_id')
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h2', class_='chapter').attrs['id']}s{article_id}"
                else:
                    raise Exception('header2 pattern Not found...')
            elif class_name == self.dictionary_to_store_class_name['h3']:
                tag.name = "h3"
                tag['class'] = "section"
                if re.search("^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?|^Chs. \d+  - \d+\.",
                             tag.text.strip()):
                    if re.search("^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?", tag.text.strip()):
                        id_of_section = re.search("^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?",
                                                  tag.text.strip()).group()
                    else:
                        match = re.search("^Chs. (?P<section_id>\d+  - \d+)\.", tag.text.strip()).group('section_id')
                        id_of_section = re.sub('[^A-Za-z0-9]', '', match)
                    section_id = f"{tag.find_previous_sibling('h2').attrs['id']}s{id_of_section}"
                    duplicate = self.soup.find_all("h3", id=section_id)
                    if len(duplicate):  # 4-1.1-1
                        count_for_duplicate += 1
                        tag.attrs['id'] = f"{section_id}.{str(count_for_duplicate).zfill(2)}"
                    else:
                        count_for_duplicate = 0
                        tag.attrs['id'] = section_id
                else:
                    raise Exception('section pattern not found...')
            elif class_name == self.dictionary_to_store_class_name['h4']:
                if re.search('^Cross References\.[a-zA-Z0-9]+', tag.text.strip()):
                    p_tag_for_cross_reference = self.soup.new_tag("p")
                    p_tag_for_cross_reference.string = 'Cross References.'
                    tag_text = tag.text.replace('Cross References.', '')
                    tag.insert_before(p_tag_for_cross_reference)
                    tag.clear()
                    tag.string = tag_text
                    p_tag_for_cross_reference.attrs['class'] = [self.dictionary_to_store_class_name['History']]
                    tag = p_tag_for_cross_reference

                elif re.search('^Purposes\. (\d+|\([a-z]\))', tag.text.strip()):
                    p_tag_for_purpose = self.soup.new_tag("p")
                    p_tag_for_purpose.string = 'Purposes. '
                    tag_text = tag.text.replace('Purposes. ', '')
                    tag.insert_before(p_tag_for_purpose)
                    tag.clear()
                    tag.string = tag_text
                    p_tag_for_purpose.attrs['class'] = [self.dictionary_to_store_class_name['History']]
                if tag.text.strip() in list_to_store_regex_for_h4:
                    tag.name = "h4"
                    if tag.find_previous_sibling().attrs['class'][0] == self.dictionary_to_store_class_name['li']:  # t3c13repealed section
                        tag.attrs['id'] = f"{tag.find_previous_sibling('h2').attrs['id']}-{re.sub(r'[^a-zA-Z0-9]', '', tag.text).lower()}"
                    else:
                        tag['id'] = f"{tag.find_previous_sibling('h3',class_='section').attrs['id']}-{re.sub(r'[^a-zA-Z0-9]', '', tag.text).lower()}"
                if tag.text.strip() == 'NOTES TO DECISIONS':
                    tag_id = tag.attrs['id']
                    for sub_tag in tag.find_next_siblings():
                        class_name = sub_tag.attrs['class'][0]
                        if class_name == self.dictionary_to_store_class_name['History']:
                            sub_tag.name = 'li'
                        elif class_name == self.dictionary_to_store_class_name['h4'] and sub_tag.b and re.search(
                                'Collateral References\.', sub_tag.text) is None:
                            sub_tag.name = "h5"
                            sub_tag_id = re.sub(r'[^a-zA-Z0-9]', '', sub_tag.text.strip()).lower()
                            if re.search('^—.*', sub_tag.text.strip()):
                                sub_tag.attrs[
                                    'id'] = f"{sub_tag.find_previous_sibling('h5', class_='notes_section').attrs['id']}-{sub_tag_id}"
                            else:
                                h5_id = f"{tag_id}-{sub_tag_id}"
                                duplicate = self.soup.find_all("h5", id=h5_id)
                                if len(duplicate):  # 4-1.1-1
                                    count_for_duplicate += 1
                                    sub_tag.attrs['id'] = f"{h5_id}.{str(count_for_duplicate).zfill(2)}"
                                else:
                                    count_for_duplicate = 0
                                    sub_tag.attrs['id'] = f"{h5_id}"
                                sub_tag.attrs['class'] = 'notes_section'
                        elif re.search('^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?|^Chs. \d+  - \d+\.',
                                       sub_tag.text.strip()) or re.search('Collateral References\.',sub_tag.text) or re.search(
                                '^Part (\d{1,2}|(IX|IV|V?I{0,3}))', sub_tag.text) or re.search(
                                '^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?', sub_tag.text):
                            break
            elif class_name == self.dictionary_to_store_class_name['History']:
                if re.search("^History of Section\.", tag.text.strip()):
                    h4_tag = self.soup.new_tag("h4")
                    h4_tag.string = "History of Section."
                    tag.insert_before(h4_tag)
                    tag.string = re.sub('History of Section.', '', tag.text.strip())
                    sub_section_id = re.sub(r'[^a-zA-Z0-9]', '', h4_tag.text.strip()).lower()
                    if h4_tag.find_previous_sibling().attrs['class'] == "nav_li":  # history of section
                        h4_tag.attrs['id'] = f"{h4_tag.find_previous_sibling('h2').attrs['id']}-{sub_section_id}"
                    else:
                        h4_tag.attrs['id'] = f"{h4_tag.find_previous_sibling('h3').attrs['id']}-{sub_section_id}"
                elif re.search("^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", tag.text.strip(), re.IGNORECASE):

                    if re.search("^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3}) [A-Z a-z]+", tag.text.strip(), re.IGNORECASE):
                        tag_for_article = self.soup.new_tag("h3")
                        article_number=re.search('^(ARTICLE (?P<article_id>(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})))', tag.text.strip(), re.IGNORECASE)
                        tag_for_article.string = article_number.group()
                        tag_text = tag.text.replace(f'{article_number.group()}', '')
                        tag.insert_before(tag_for_article)
                        tag.clear()
                        tag.string = tag_text
                        tag_for_article.attrs['class'] = [self.dictionary_to_store_class_name['History']]
                        tag_for_article['id'] = f"{tag.find_previous_sibling('h3', class_='section').attrs['id']}a{article_number.group('article_id')}"
                    else:
                        tag.name = "h3"
                        article_id = re.search("^ARTICLE (?P<article_id>(XC|XL|L?X{0,3})(IX|IV|V?I{0,3}))",tag.text.strip(), re.IGNORECASE).group('article_id')
                        tag['id'] = f"{tag.find_previous_sibling('h3', class_='section').attrs['id']}a{article_id}"
                elif re.search("^Section \d+. [a-z ,\-A-Z]+\. \(a\)", tag.text.strip()) and re.search("^\(b\)",
                                                                                                      tag.find_next_sibling().text.strip()):  # section 14
                    text_from_b = tag.text.split('(a)')
                    p_tag_for_section = self.soup.new_tag("p")
                    p_tag_for_section.string = text_from_b[0]
                    p_tag_for_a = self.soup.new_tag("p")
                    p_tag_text = f"(a){text_from_b[1]}"
                    p_tag_for_a.string = p_tag_text
                    tag.insert_before(p_tag_for_section)
                    tag.insert_before(p_tag_for_a)
                    p_tag_for_a.attrs['class'] = [self.dictionary_to_store_class_name['History']]
                    p_tag_for_section.attrs['class'] = [self.dictionary_to_store_class_name['History']]
                    tag.decompose()
                elif re.search('^Schedule (IX|IV|V?I{0,3})', tag.text.strip()):
                    tag.name = "h4"
                    tag['class']='schedule'
                    schedule_id = re.search('^Schedule (?P<schedule_id>(IX|IV|V?I{0,3}))', tag.text.strip()).group('schedule_id')
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h3', class_='section').attrs['id']}sec{schedule_id}"
            elif class_name == self.dictionary_to_store_class_name['li']:
                if re.search("^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?", tag.text.strip()) or re.search(
                        "^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?|^Chs. \d+  - \d+\.",
                        tag.text.strip()) or re.search('^Part (\d{1,2}|(IX|IV|V?I{0,3}))',
                                                       tag.text.strip()) or re.search('^Subpart [A-Z0-9]',
                                                                                      tag.text.strip()) or re.search(
                        '^Article (\d+|(IX|IV|V?I{0,3}))', tag.text.strip()):
                    tag.name = "li"
                    tag['class'] = "nav_li"

    def create_li_with_anchor(self, li_tag, id, li_type=None, li_count=None):
        li_tag_text = li_tag.text
        li_tag.clear()
        li_tag.append(self.soup.new_tag("a", href='#' + id))
        li_tag.a.string = li_tag_text
        if li_type:
            li_tag['id'] = f"{id}-{li_type}{str(li_count).zfill(2)}"
        return li_tag

    def create_nav_and_ul_tag(self):
        ul_tag_for_chapter = self.soup.new_tag("ul")
        ul_tag_for_section = self.soup.new_tag("ul")
        ul_tag_for_header5 = self.soup.new_tag("ul")
        ul_tag_for_sub_section = self.soup.new_tag("ul")
        ul_tag_for_part = self.soup.new_tag("ul")
        ul_tag_for_article = self.soup.new_tag("ul")
        ul_tag_for_sub_part = self.soup.new_tag("ul")
        li_count_for_chapter = 0
        li_count_for_section = 0
        li_count_for_part = 0
        li_count_for_sub_part = 0
        li_count_for_article = 0
        count_for_duplicate = 0
        nav_tag_for_sub_part_ul = self.soup.new_tag("nav")
        nav_tag_for_part_ul = self.soup.new_tag("nav")
        nav_tag_for_notes_to_decision_ul = self.soup.new_tag("nav")
        nav_tag_for_article_ul = self.soup.new_tag("nav")
        for li_tag in self.soup.find_all("li"):
            if re.search("^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?", li_tag.text.strip()):
                chapter_number = re.search("^Chapters? (?P<chapter_number>\d+(\.\d+)?(\.\d+)?([A-Z])?)",
                                           li_tag.text.strip()).group('chapter_number').zfill(2)
                h1_id = f"{li_tag.find_previous_sibling('h1').attrs['id']}c{chapter_number}"
                li_count_for_chapter += 1
                li_tag = self.create_li_with_anchor(li_tag, h1_id, "cnav", li_count_for_chapter)
                ul_tag_for_chapter.attrs['class'] = 'leaders'
                li_tag.wrap(ul_tag_for_chapter)
            elif re.search(
                    "^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?|^Chs. \d+  - \d+\.|^Article \d+",
                    li_tag.text.strip()):
                nav_tag_for_section_ul = self.soup.new_tag("nav")
                if re.search("^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?", li_tag.text.strip()):
                    section_id = re.search("^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?",
                                           li_tag.text.strip()).group()
                elif re.search('^Article \d+', li_tag.text.strip()):
                    section_id = re.search('^Article (?P<article_id>\d+)', li_tag.text.strip()).group('article_id')
                else:
                    match = re.search('^Chs. (?P<section_id>\d+  - \d+)\.', li_tag.text.strip()).group('section_id')
                    section_id = re.sub('[^A-Za-z0-9]', '', match)
                h3_id = f"{li_tag.find_previous_sibling('h2').attrs['id']}s{section_id}"
                duplicate = self.soup.find_all("a", href='#' + h3_id)
                if len(duplicate):
                    count_for_duplicate += 1
                    id_count = str(count_for_duplicate).zfill(2)
                    h3_id = f"{h3_id}.{id_count}"
                else:
                    count_for_duplicate = 0
                li_count_for_section += 1
                li_tag = self.create_li_with_anchor(li_tag, h3_id, "snav", li_count_for_section)
                next_tag = li_tag.find_next_sibling()
                ul_tag_for_section.attrs['class'] = 'leaders'
                if next_tag.name == "h3" or next_tag.name == "h4":
                    li_tag.wrap(ul_tag_for_section)
                    ul_tag_for_section.wrap(nav_tag_for_section_ul)
                    ul_tag_for_section = self.soup.new_tag("ul")
                    nav_tag_for_section_ul = self.soup.new_tag("nav")
                    li_count_for_section = 0
                else:
                    li_tag.wrap(ul_tag_for_section)
            elif re.search("^Part (\d{1,2}|(IX|IV|V?I{0,3}))", li_tag.text.strip()):
                part_id = re.search("^Part (?P<part_number>\d{1,2}|(IX|IV|V?I{0,3}))", li_tag.text.strip()).group(
                    'part_number').zfill(2)
                h2_id = li_tag.find_previous_sibling('h2').attrs['id']
                li_count_for_part += 1
                li_tag = self.create_li_with_anchor(li_tag, f"{h2_id}p{part_id}", "snav", li_count_for_part)
                next_tag = li_tag.find_next_sibling()
                ul_tag_for_part.attrs['class'] = 'leaders'
                if next_tag.name == "h2":
                    li_tag.wrap(ul_tag_for_part)
                    ul_tag_for_part.wrap(nav_tag_for_part_ul)
                    ul_tag_for_part = self.soup.new_tag("ul")
                    nav_tag_for_part_ul = self.soup.new_tag("nav")
                    li_count_for_part = 0
                else:
                    li_tag.wrap(ul_tag_for_part)
            elif re.search('^Article (IX|IV|V?I{0,3})', li_tag.text.strip()):
                article_id = re.search('^Article (?P<article_id>(IX|IV|V?I{0,3}))', li_tag.text.strip()).group(
                    'article_id')
                h2_id = li_tag.find_previous_sibling('h2').attrs['id']
                li_count_for_article += 1
                li_tag = self.create_li_with_anchor(li_tag, f"{h2_id}s{article_id}", "snav", li_count_for_article)
                next_tag = li_tag.find_next_sibling()
                ul_tag_for_article.attrs['class'] = 'leaders'
                if next_tag.name == "h2":
                    li_tag.wrap(ul_tag_for_article)
                    ul_tag_for_article.wrap(nav_tag_for_article_ul)
                    ul_tag_for_article = self.soup.new_tag("ul")
                    nav_tag_for_article_ul = self.soup.new_tag("nav")
                    li_count_for_article = 0
                else:
                    li_tag.wrap(ul_tag_for_article)
            elif re.search('^Subpart [A-Z0-9]', li_tag.text.strip()):
                sub_part_id = re.search("^Subpart (?P<sub_part_number>[A-Z0-9])", li_tag.text.strip()).group(
                    'sub_part_number')
                h2_id = li_tag.find_previous_sibling('h2').attrs['id']
                li_count_for_sub_part += 1
                li_tag = self.create_li_with_anchor(li_tag, f"{h2_id}sp{sub_part_id}", "snav", li_count_for_part)
                next_tag = li_tag.find_next_sibling()
                ul_tag_for_sub_part.attrs['class'] = 'leaders'
                if next_tag.name == "h2":
                    li_tag.wrap(ul_tag_for_sub_part)
                    ul_tag_for_sub_part.wrap(nav_tag_for_sub_part_ul)
                    ul_tag_for_sub_part = self.soup.new_tag("ul")
                    nav_tag_for_sub_part_ul = self.soup.new_tag("nav")
                    li_count_for_sub_part = 0
                else:
                    li_tag.wrap(ul_tag_for_sub_part)

            else:
                ul_tag_for_sub_section.attrs['class'] = 'leaders'
                ul_tag_for_header5.attrs['class'] = 'leaders'
                h4_id = li_tag.find_previous_sibling("h4").attrs['id']
                sub_section_id = re.sub(r'[^a-zA-Z0-9]', '', li_tag.text.strip()).lower()
                if re.search('^—.*', li_tag.text.strip()):
                    id_of_parent = re.sub(r'[^a-zA-Z0-9]', '',
                                          li_tag.find_previous_sibling().find_all("li", class_="notes_to_decision")[
                                              -1].text).lower()
                    h5_id = f"{h4_id}-{id_of_parent}-{sub_section_id}"
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    if re.search('^—.*', li_tag.find_next_sibling().text.strip()):
                        li_tag.wrap(ul_tag_for_sub_section)
                        ul_tag_for_header5.append(ul_tag_for_sub_section)
                    elif li_tag.find_next_sibling().name == "h5":
                        li_tag.wrap(ul_tag_for_sub_section)
                        ul_tag_for_header5.find_all("li")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                        ul_tag_for_header5.wrap(nav_tag_for_notes_to_decision_ul)
                        ul_tag_for_header5 = self.soup.new_tag("ul")
                    else:
                        li_tag.wrap(ul_tag_for_sub_section)
                        ul_tag_for_header5.find_all("li")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                else:
                    h5_id = f"{h4_id}-{sub_section_id}"
                    duplicate = self.soup.find_all("a", href='#' + h5_id)
                    if len(duplicate):
                        count_for_duplicate += 1
                        id_count = str(count_for_duplicate).zfill(2)
                        h5_id = f"{h5_id}.{id_count}"
                    else:
                        count_for_duplicate = 0
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    li_tag['class'] = 'notes_to_decision'
                    if li_tag.find_next_sibling().name == "h5":
                        li_tag.wrap(ul_tag_for_header5)
                        ul_tag_for_header5.wrap(nav_tag_for_notes_to_decision_ul)
                        ul_tag_for_header5 = self.soup.new_tag("ul")
                        nav_tag_for_notes_to_decision_ul = self.soup.new_tag("nav")
                    else:
                        li_tag.wrap(ul_tag_for_header5)

    def create_nav_and_main_tag(self):
        nav_tag_for_header1_and_chapter = self.soup.new_tag("nav")
        p_tag = self.soup.new_tag("p")
        p_tag['class'] = "transformation"
        p_tag.string = f"Release {self.release_number} of the Official Code of Rhode Island Annotated released 2021.11. Transformed and posted by Public.Resource.Org using rtf-parser.py version 1.0 on 2022-06-13. This document is not subject to copyright and is in the public domain."
        nav_tag_for_header1_and_chapter.append(p_tag)
        main_tag = self.soup.new_tag("main")
        self.soup.find("h1").wrap(nav_tag_for_header1_and_chapter)
        self.soup.find("ul").wrap(nav_tag_for_header1_and_chapter)
        for tag in nav_tag_for_header1_and_chapter.find_next_siblings():
            tag.wrap(main_tag)

    def add_citation(self):
        for tag in self.soup.find_all(["p", "li"]):
            if re.search('P.L. 1936 , ch. 2334, § 9; G.L. 1938 , ch. 18, § 9; P.L. 1947 , ch. 1971, § 7; P.L',tag.text):
                print()
            if tag['class'] not in ["notes_to_decision", "notes_section"]:
                tag_string = ''
                text = str(tag)
                text = re.sub('^<p[^>]*>|</p>$', '', text.strip())
                cite_tag_pattern = {
                    'alr_pattern': '\d+ A.L.R.( Fed. )?(\d[a-z]{1,2})?( Art.)? ?\d+|\d+ A. Fed. (\d[a-z]{1,2})?( Art.)? ?\d+',
                    'pl_pattern': '(impl\. am\. )?P\.L\. \d+',
                    'gl_pattern': '(G\.L\. ?\d+)',
                    'us_ammend': 'U\.S\. Const\., Amend\. (\d+|(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\.)( C)?',
                    'sct': '(\d+ S\. Ct\. \d+)',
                    'led': '(\d+ L\. Ed\. \d+[a-z] \d+)',
                    'ann_laws': '(Ann\. Laws ch\. \d+)',
                    'ri': '(\d+ R\.I\. \d+)',
                    'ri_lexis': '(\d+ R\.I\. LEXIS \d+)',
                    'us': '(\d+ U\.S\. \d+)',
                    'us_lexis': '(\d+ U\.S\. LEXIS \d+)',
                    'a_2d': '(\d+ A\.2d \d+)',
                    'roger': '\d+ R(\.|oger )W(\.|illiams )U\. ?L\. Rev. \d+',
                    'cfr': '(\d+ CFR \d+\.\d+(?!\d+-))',
                    'usc': '(\d+ U\.S\.C\.)',
                    'supp': '(\d+ F\. Supp\. \d+)',
                    'us_dist_lexis': '(U\.S\. Dist\. LEXIS \d+)'
                }
                for key in cite_tag_pattern:
                    cite_pattern = cite_tag_pattern[key]
                    if re.search(cite_pattern, tag.text.strip()) and tag.attrs['class'] != "nav_li":
                        for cite_pattern in set(
                                match[0] for match in re.findall('(' + cite_tag_pattern[key] + ')', tag.text.strip())):
                            tag_string = re.sub(cite_pattern, f'<cite class="ocri">{cite_pattern}</cite>', text)
                            text = tag_string

                if re.search('\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?((\([a-z 0-9 (ix|iv|v?i{0,3}) A-Z 0-9]{1,3}\) ?)+)?',tag.text.strip()) and tag.attrs['class'] != "nav_li":
                    for pattern in sorted(set(match[0] for match in re.findall(
                            '(\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?((\([a-z 0-9 (ix|iv|v?i{0,3}) A-Z 0-9]{1,3}\) ?)+)?)',
                            tag.text.strip()))):
                        section_match = re.search("(?P<section_id>(?P<title_id>\d+[A-Z]?(\.\d+)?)-(?P<chapter_id>\d+)(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?)",pattern)
                        file_exists = exists(
                            f'/home/mis/PycharmProjects/practice/venv/ricode/modified/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html')
                        if file_exists:
                            file = open(
                                f'/home/mis/PycharmProjects/practice/venv/ricode/modified/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html')
                            content = file.read()
                            file.close()
                        else:
                            continue
                        if re.search(f'\d+[A-Z]?(\.\d+)?-\d+(-\d+)?([A-Z])?(\.\d+(-\d+)?(\.\d+)?(-\d+)?)?(\([a-z 0-9 (ix|iv|v?i{0, 3}) A-Z ]+\) ?)+',pattern.strip()):
                            match = re.search(f'(\([a-z 0-9 (ix|iv|v?i{0, 3}) A-Z ]+\) ?)+', pattern.strip()).group()
                            match = match.replace('(', '').replace(')', '')
                            if re.search('[A-Z]', match):
                                caps_alpha = re.search('(?P<caps_alpha>([A-Z]))', match).group('caps_alpha')
                                match = match.replace(caps_alpha, f'-{caps_alpha}')
                            section_id = section_match.group('section_id')
                            if re.search(f'id=".+s{section_id}ol1{match}"', content):
                                tag_id = re.search(f'id="(?P<tag_id>(.+s{section_id}ol1{match}))"', content).group(
                                    'tag_id')
                                tag_string = re.sub(fr'{re.escape(pattern)}',
                                                    f'<cite class="ocri"><a href=http://localhost:63342/practice/venv/ricode/modified/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html?_ijt=lartillgujbilc2c7ak6tlmhr8&_ij_reload=RELOAD_ON_SAVE#{tag_id} target="_self">{pattern}</a></cite>',
                                                    text)

                        elif re.search('\d+[A-Z]?(\.\d+)?-\d+-\d+\.\d+', pattern):
                            if re.search(f'id=".+s{pattern}"', content):
                                tag_id = re.search(f'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                tag_string = re.sub(fr'{re.escape(pattern)}',f'<cite class="ocri"><a href=http://localhost:63342/practice/venv/ricode/modified/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html?_ijt=lartillgujbilc2c7ak6tlmhr8&_ij_reload=RELOAD_ON_SAVE#{tag_id} target="_self">{pattern}</a></cite>',text)

                        else:
                            if re.search('(?<!\.|-)\d+[A-Z]?(\.\d+)?-\d+(?!((\d)?\.\d+)|((\d)?-\d+))',
                                         pattern):  # 12-32
                                chapter_id = section_match.group('chapter_id').zfill(2)
                                if re.search(f'id=".+c{chapter_id}"', content):
                                    tag_id = re.search(f'id="(?P<tag_id>(.+c{chapter_id}))"', content).group('tag_id')
                                    tag_string = re.sub(fr'{re.escape(pattern)}',f'<cite class="ocri"><a href=http://localhost:63342/practice/venv/ricode/practice/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html?_ijt=lartillgujbilc2c7ak6tlmhr8&_ij_reload=RELOAD_ON_SAVE#{tag_id} target="_self">{pattern}</a></cite>',
                                                        text)
                            else:
                                if re.search('\d+[A-Z]?(\.\d+)?-\d+-\d(?!(\d+))', pattern):
                                    if re.search(f'id=".+s{pattern}"', content):
                                        tag_id = re.search(f'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        tag_string = re.sub(fr'{re.escape(pattern)}' + '(?!((\d)?\.\d+)|(\d+))',f'<cite class="ocri"><a href=http://localhost:63342/practice/venv/ricode/modified/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html?_ijt=lartillgujbilc2c7ak6tlmhr8&_ij_reload=RELOAD_ON_SAVE#{tag_id} target="_self">{pattern}</a></cite>',text)
                                elif re.search('\d+[A-Z]?(\.\d+)?-\d+-\d+([a-z])?(?!\.\d+)', pattern):
                                    if re.search(f'id=".+s{pattern}"', content):
                                        tag_id = re.search(f'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        tag_string = re.sub(fr'{re.escape(pattern)}' + '(?!((\d)?\.\d+))',f'<cite class="ocri"><a href=http://localhost:63342/practice/venv/ricode/modified/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html?_ijt=lartillgujbilc2c7ak6tlmhr8&_ij_reload=RELOAD_ON_SAVE#{tag_id} target="_self">{pattern}</a></cite>',text)
                                elif re.search('\d+[A-Z]?(\.\d+)?-\d+\.\d+(\.\d+)?-\d+(\.\d+)?', pattern):
                                    if re.search(f'id=".+s{pattern}"', content):
                                        tag_id = re.search(f'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        tag_string = re.sub(fr'{re.escape(pattern)}',f'<cite class="ocri"><a href=http://localhost:63342/practice/venv/ricode/modified/gov.ri.code.title.{section_match.group("title_id").zfill(2)}.html?_ijt=lartillgujbilc2c7ak6tlmhr8&_ij_reload=RELOAD_ON_SAVE#{tag_id} target="_self">{pattern}</a></cite>',text)
                        text = tag_string
                if tag_string:
                    tag_class = tag['class']
                    tag.clear()
                    tag.append(BeautifulSoup(tag_string, features="html.parser"))
                    tag['class'] = tag_class
        print('cited')
    def create_ol_tag(self):
        alphabet = 'a'
        number = 1
        roman_number = 'i'
        inner_roman = 'i'
        caps_alpha = 'A'
        inner_num = 1
        caps_roman = 'I'
        inner_alphabet = 'a'
        ol_count = 1
        ol_tag_for_roman = self.soup.new_tag("ol", type='i')
        ol_tag_for_number = self.soup.new_tag("ol")
        ol_tag_for_alphabet = self.soup.new_tag("ol", type='a')
        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
        ol_tag_for_inner_number = self.soup.new_tag("ol")
        ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
        ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
        count_of_p_tag = 1
        comment_count = 0
        for tag in self.soup.main.find_all("p"):
            print(tag)
            if not tag.name:
                tag.decompose()
                continue
            class_name = tag['class'][0]
            if tag.find_previous_sibling("h3"):
                h3_id=tag.find_previous_sibling("h3").attrs['id']
            else:
                h3_id = tag.find_previous_sibling("h3",class_="section").attrs['id']
            if class_name == self.dictionary_to_store_class_name['History'] or class_name == self.dictionary_to_store_class_name['ol_of_i'] :
                if re.search("^“?[a-z A-Z]+", tag.text.strip()):
                    next_sibling = tag.find_next_sibling()
                    if next_sibling and tag.name == "h3":
                        ol_count = 1
                if tag.i:
                    tag.i.unwrap()
                next_tag = tag.find_next_sibling()
                if not next_tag:  # last tag
                    break
                if next_tag.next_element.name and next_tag.next_element.name == 'br':
                    next_tag.decompose()
                    next_tag = tag.find_next_sibling()
                if next_tag and next_tag.name == "h3":
                    comment_count = 0
                if re.search('Registry identification cards shall contain:',tag.text.strip()):
                    print()
                if re.search(f'^{number}\.', tag.text.strip()):
                    tag.name = "li"
                    text = str(tag)
                    tag_string = re.sub(
                        '^<li[^>]*>(<span.*</span>)?<b>\d{1,2}\.</b>|^<li[^>]*>(<span.*</span>)?\d{1,2}\.|</li>$',
                        '', text.strip())
                    tag.clear()
                    tag.append(BeautifulSoup(tag_string, features="html.parser"))
                    tag['class'] = "number"
                    if re.search('OFFICIAL COMMENT|COMMISSIONER’S COMMENT',
                                 tag.find_previous_sibling('h4').text.strip()):
                        tag['id'] = f"{tag.find_previous_sibling('h4').attrs['id']}ol{ol_count}{number}"
                    elif ol_tag_for_alphabet.li:
                        tag['id'] = f"{ol_tag_for_alphabet.find_all('li',class_='alphabet')[-1].attrs['id']}{number}"
                    else:
                        tag['id'] = f"{tag.find_previous_sibling('h3',class_='section').attrs['id']}ol{ol_count}{number}"
                    tag.wrap(ol_tag_for_number)
                    number += 1
                    while (next_tag.name != "h4" and next_tag.name != "h3") and re.search('^“?[a-z A-Z]+', next_tag.text.strip()):
                        sub_tag = next_tag.find_next_sibling()
                        p_tag = self.soup.new_tag("p")
                        p_tag.string = next_tag.text
                        p_tag['id'] = f"{tag['id']}.{count_of_p_tag}"
                        count_of_p_tag += 1
                        p_tag['class'] = next_tag['class']
                        tag.append(p_tag)
                        next_tag.decompose()
                        next_tag = sub_tag
                    count_of_p_tag = 1
                    if re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', next_tag.text.strip()):
                        if ol_tag_for_alphabet.li:
                            ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                            ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                            alphabet = 'a'
                        ol_tag_for_number = self.soup.new_tag("ol")
                        number = 1
                        ol_count = 1
                    elif next_tag.name == "h3" or next_tag.name == "h4":
                        ol_tag_for_number = self.soup.new_tag("ol")
                        number = 1
                    elif re.search(f'^\({alphabet}\)',next_tag.text.strip()):
                        ol_tag_for_alphabet.find_all("li",class_="alphabet")[-1].append(ol_tag_for_number)
                        ol_tag_for_number=self.soup.new_tag("ol")
                        number=1
                elif re.search(f'^\({caps_alpha}{caps_alpha}?\)', tag.text.strip()):
                    if re.search(f'^\({caps_alpha}{caps_alpha}?\) \({caps_roman}\)',tag.text.strip()):
                        if re.search(f'^\({caps_alpha}{caps_alpha}?\) \({caps_roman}\) \({inner_alphabet}\)', tag.text.strip()):
                            tag.name = "li"
                            text = str(tag)
                            caps_alpha_id=re.search(f'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)', tag.text.strip()).group('caps_alpha_id')
                            tag_string = re.sub(
                                f'^<li[^>]*>(<span.*</span>)?<b>\({caps_alpha}{caps_alpha}?\) \({caps_roman}\) \({inner_alphabet}\)</b>|^<li[^>]*>(<span.*</span>)?\({caps_alpha}\) \({caps_roman}\) \({inner_alphabet}\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_inner_alphabet)
                            li_tag_for_caps_alpha = self.soup.new_tag("li")
                            li_tag_for_caps_alpha['id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}"
                            li_tag_for_caps_roman = self.soup.new_tag("li")
                            li_tag_for_caps_roman['id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}"
                            li_tag_for_caps_alpha['class'] = "caps_alpha"
                            tag.attrs['id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}{inner_alphabet}"
                            tag['class'] = "inner_alpha"
                            li_tag_for_caps_roman['class'] = "caps_roman"
                            li_tag_for_caps_roman.append(ol_tag_for_inner_alphabet)
                            ol_tag_for_caps_roman.append(li_tag_for_caps_roman)
                            li_tag_for_caps_alpha.append(ol_tag_for_caps_roman)
                            ol_tag_for_caps_alphabet.append(li_tag_for_caps_alpha)
                            caps_roman = roman.fromRoman(caps_roman)
                            caps_roman += 1
                            caps_roman = roman.toRoman(caps_roman)
                            if caps_alpha=='Z':
                                caps_alpha='A'
                            else:
                                caps_alpha = chr(ord(caps_alpha) + 1)
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                        else:
                            tag.name = "li"
                            text = str(tag)
                            caps_alpha_id = re.search(f'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',tag.text.strip()).group('caps_alpha_id')
                            tag_string = re.sub(
                                f'^<li[^>]*>(<span.*</span>)?<b>\({caps_alpha}{caps_alpha}?\) \({caps_roman}\)</b>|^<li[^>]*>(<span.*</span>)?\({caps_alpha}\) \({caps_roman}\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_caps_roman)
                            li_tag_for_caps_alpha = self.soup.new_tag("li")
                            if ol_tag_for_roman.li:
                                li_tag_for_caps_alpha['id'] = f"{ol_tag_for_roman.find_all('li', class_='roman')[-1].attrs['id']}-{caps_alpha_id}"
                                tag.attrs['id'] = f"{ol_tag_for_roman.find_all('li', class_='roman')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}"
                            else:
                                li_tag_for_caps_alpha['id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}"
                                tag.attrs['id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}"
                            li_tag_for_caps_alpha['class'] = "caps_alpha"
                            tag['class'] = "caps_roman"
                            li_tag_for_caps_alpha.append(ol_tag_for_caps_roman)
                            ol_tag_for_caps_alphabet.append(li_tag_for_caps_alpha)
                            caps_roman = roman.fromRoman(caps_roman)
                            caps_roman += 1
                            caps_roman = roman.toRoman(caps_roman)
                            if caps_alpha == 'Z':
                                caps_alpha = 'A'
                            else:
                                caps_alpha = chr(ord(caps_alpha) + 1)
                    else:
                        tag.name = "li"
                        text = str(tag)
                        caps_alpha_id = re.search(f'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',tag.text.strip()).group('caps_alpha_id')
                        tag_string = re.sub(
                            f'^<li[^>]*>(<span.*</span>)?<b>\({caps_alpha}{caps_alpha}?\)</b>|^<li[^>]*>(<span.*</span>)?\({caps_alpha}{caps_alpha}?\)|</li>$',
                            '', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        tag['class'] = "caps_alpha"
                        tag.wrap(ol_tag_for_caps_alphabet)
                        if ol_tag_for_roman.li:
                            id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                        else:
                            id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                        tag['id'] = f"{id_of_last_li}-{caps_alpha_id}"
                        if caps_alpha == "Z":
                            caps_alpha = 'A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                        while re.search("^[a-z A-Z]+", next_tag.text.strip()) and next_tag.name != "h4":
                            sub_tag = next_tag.find_next_sibling()
                            p_tag = self.soup.new_tag("p")
                            p_tag.string = next_tag.text
                            p_tag['class'] = next_tag['class']
                            tag.append(p_tag)
                            id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                            p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                            count_of_p_tag += 1
                            p_tag['class'] = next_tag['class']
                            next_tag.decompose()
                            ol_tag_for_caps_alphabet.append(tag)
                            next_tag = sub_tag
                        count_of_p_tag = 1
                        if re.search(f'^\({inner_roman}\)', next_tag.text.strip()) and ol_tag_for_caps_alphabet.li:
                            continue
                        elif re.search(f'^\({roman_number}\)', next_tag.text.strip()):
                            if ol_tag_for_roman.li:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                        elif re.search(f'^\({number}\)', next_tag.text.strip()):
                            if ol_tag_for_roman.li:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                            else:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                    ol_tag_for_caps_alphabet)
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                        elif re.search(f'^\({inner_alphabet}\)', next_tag.text.strip()) and ol_tag_for_number.li:
                            if ol_tag_for_roman.li:  # 1aiAb
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                ol_tag_for_inner_alphabet.find_all("li",class_="inner_alpha")[-1].append(ol_tag_for_roman)
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                        elif re.search(f'^\({alphabet}\)', next_tag.text.strip()):
                            if ol_tag_for_roman.li:  # a1iAb
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                if ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                        ol_tag_for_number)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = 'i'
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                else:
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                        ol_tag_for_roman)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = 'i'
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                            else:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                    ol_tag_for_caps_alphabet)
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                        elif next_tag.name=="h4":
                            if ol_tag_for_roman.li:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                if ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    if ol_tag_for_alphabet.li:
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                        ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                        alphabet = 'a'
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                else:
                                    ol_tag_for_alphabet.find_all("li",class_="alphabet")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                    alphabet = 'a'
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = "i"
                            else:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_caps_alphabet)
                                if ol_tag_for_alphabet.li:
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                    alphabet = 'a'
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                            if re.search('^Schedule (IX|IV|V?I{0,3})',next_tag.text.strip()):
                                comment_count = 1
                elif re.search(f'^\({caps_roman}\)', tag.text.strip()):
                    tag.name = "li"
                    text = str(tag)
                    tag_string = re.sub(
                        '^<li[^>]*>(<span.*</span>)?<b>\((XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\)</b>|^<li[^>]*>(<span.*</span>)?\((XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\)|</li>$',
                        '', text.strip())
                    tag.clear()
                    tag.append(BeautifulSoup(tag_string, features="html.parser"))
                    if ol_tag_for_caps_roman.li:
                        ol_tag_for_caps_roman.append(tag)
                    else:
                        tag.wrap(ol_tag_for_caps_roman)
                    if ol_tag_for_caps_alphabet.li:
                        id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                    else:
                        id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                    tag['id'] = f"{id_of_last_li}-{caps_roman}"
                    tag['class'] = "caps_roman"
                    caps_roman = roman.fromRoman(caps_roman)
                    caps_roman += 1
                    caps_roman = roman.toRoman(caps_roman)
                    while re.search("^[a-z A-Z]+", next_tag.text.strip()) and next_tag.name != "h4":
                        sub_tag = next_tag.find_next_sibling()
                        p_tag = self.soup.new_tag("p")
                        p_tag.string = next_tag.text
                        p_tag['class'] = next_tag['class']
                        tag.append(p_tag)
                        id_of_last_li = ol_tag_for_caps_roman.find_all("li")[-1].attrs['id']
                        p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                        count_of_p_tag += 1
                        p_tag['class'] = next_tag['class']
                        next_tag.decompose()
                        ol_tag_for_caps_roman.append(tag)
                        next_tag = sub_tag
                    count_of_p_tag = 1
                    if re.search(f'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()):
                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_caps_roman)
                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                        caps_roman = 'I'
                    elif re.search(f'^\({roman_number}\)', next_tag.text.strip()) and roman_number != "i":
                        if ol_tag_for_caps_alphabet.li:
                            ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_caps_roman)
                            ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                            ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                            caps_roman = 'I'
                            ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                            caps_alpha = 'A'
                        else:
                            ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_roman)
                            ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                            caps_roman = 'I'
                    elif re.search(f'^\({number}\)', next_tag.text.strip()):
                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_caps_roman)
                        if ol_tag_for_roman.li:
                            ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                            ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                            roman_number = "i"
                        else:
                            ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_caps_alphabet)
                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                        caps_roman = 'I'
                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                        caps_alpha = 'A'
                elif re.search(f'^\({roman_number}\)|^\({inner_roman}\)', tag.text.strip()) and (ol_tag_for_number.li or alphabet != roman_number):
                    if re.search(f'^\({roman_number}\) \({caps_alpha}{caps_alpha}?\)', tag.text.strip()):
                        caps_alpha_id = re.search(f'\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',tag.text.strip()).group('caps_alpha_id')
                        tag.name = "li"
                        text = str(tag)
                        tag_string = re.sub(
                            '^<li[^>]*>(<span.*</span>)?<b>\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\) \([A-Z]\)</b>|^<li[^>]*>(<span.*</span>)?\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\) \([A-Z]\)|</li>$',
                            '', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        tag['class'] = "caps_alpha"
                        tag.wrap(ol_tag_for_caps_alphabet)
                        li_tag = self.soup.new_tag("li")
                        if ol_tag_for_number.li:
                            id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                        elif ol_tag_for_alphabet.li:
                            id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs['id']
                        li_tag['id'] = f"{id_of_last_li}{roman_number}"
                        li_tag['class'] = "roman"
                        li_tag.append(ol_tag_for_caps_alphabet)
                        tag.attrs['id'] = f"{id_of_last_li}{roman_number}-{caps_alpha_id}"
                        if caps_alpha=='Z':
                            caps_alpha='A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                        ol_tag_for_roman.append(li_tag)
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                    elif re.search(f'^\({inner_roman}\)', tag.text.strip()) and ol_tag_for_caps_alphabet.li:
                        tag.name = "li"
                        text = str(tag)
                        tag_string = re.sub(
                            f'^<li[^>]*>(<span.*</span>)?<b>\({inner_roman}\)</b>|^<li[^>]*>(<span.*</span>)?\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\)|</li>$',
                            '', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        tag.wrap(ol_tag_for_inner_roman)
                        if ol_tag_for_inner_number.li:
                            id_of_last_li = ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].attrs['id']
                        elif ol_tag_for_caps_roman.li:
                            id_of_last_li = ol_tag_for_caps_roman.find_all("li")[-1].attrs['id']
                        elif ol_tag_for_caps_alphabet.li:
                            id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                        tag['id'] = f"{id_of_last_li}{inner_roman}"
                        inner_roman = roman.fromRoman(inner_roman.upper())
                        inner_roman += 1
                        inner_roman = roman.toRoman(inner_roman).lower()
                        if re.search(f'^\({number}\)', next_tag.text.strip()):
                            if ol_tag_for_inner_number.li:
                                ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                                if ol_tag_for_caps_alphabet.li:
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                                    if ol_tag_for_roman.li:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_caps_alphabet)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = "A"
                                    else:
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_caps_alphabet)
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = "A"
                                else:
                                    if ol_tag_for_roman.li:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_inner_number)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                        ol_tag_for_inner_number = self.soup.new_tag("ol")
                                        inner_num = 1
                            elif ol_tag_for_caps_alphabet.li:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = "A"
                                else:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_caps_alphabet)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = "A"
                        elif re.search(f'^\({inner_num}\)', next_tag.text.strip()):
                            if ol_tag_for_inner_number.li:
                                ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                        elif re.search(f'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()):
                            if ol_tag_for_inner_number.li:
                                ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                                if ol_tag_for_caps_alphabet.li:
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                            elif ol_tag_for_caps_alphabet.li:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                        elif re.search(f'^\({alphabet}\)', next_tag.text.strip()):
                            if ol_tag_for_inner_number.li:
                                ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                                if ol_tag_for_caps_alphabet.li:
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                                    if ol_tag_for_roman.li:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_caps_alphabet)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_number)
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = "A"
                                        ol_tag_for_number = self.soup.new_tag("ol")
                                        number = 1
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                    else:
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_caps_alphabet)
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_number)
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = "A"
                                        ol_tag_for_number = self.soup.new_tag("ol")
                                        number = 1
                                else:
                                    if ol_tag_for_roman.li:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_inner_number)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_number)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                        ol_tag_for_number = self.soup.new_tag("ol")
                                        number = 1
                                        ol_tag_for_inner_number = self.soup.new_tag("ol")
                                        inner_num = 1
                            elif ol_tag_for_caps_alphabet.li:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = "A"
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                else:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_caps_alphabet)
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = "A"
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                        elif re.search(f'\({caps_roman}\)', next_tag.text.strip()):
                                    ol_tag_for_caps_roman.find_all("li")[-1].append(ol_tag_for_inner_roman)
                                    ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                    inner_roman = "i"
                    else:
                        tag.name = "li"
                        text = str(tag)
                        tag_string = re.sub(f'^<li[^>]*>(<span.*</span>)?<b>\({roman_number}\)</b>|^<li[^>]*>(<span.*</span>)?\({roman_number}\)|</li>$','', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        if ol_tag_for_roman.li:
                            ol_tag_for_roman.append(tag)
                        else:
                            tag.wrap(ol_tag_for_roman)
                        tag['class'] = "roman"
                        if ol_tag_for_inner_alphabet.li:
                            id_of_last_li = ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs['id']
                        elif ol_tag_for_number.li:
                            id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                        elif ol_tag_for_alphabet.li:
                            id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs['id']
                        else:
                            id_of_last_li=h3_id
                        tag['id'] = f"{id_of_last_li}{roman_number}"
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                        while next_tag.name != "h4" and (re.search('^“?[a-z A-Z]+|^\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\)|^\([A-Z]\)',next_tag.text.strip()) or (next_tag.next_element and next_tag.next_element.name == "br")):  # 5-31.1-1. after 16i 2 break
                            if next_tag.next_element.name == "br":
                                sub_tag = next_tag.find_next_sibling()
                                next_tag.decompose()
                                next_tag = sub_tag
                            elif re.search("^“?[a-z A-Z]+|^\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\)|^\([A-Z]\)", next_tag.text.strip()):
                                if re.search("^“?[a-z A-Z]+", next_tag.text.strip()):
                                    sub_tag = next_tag.find_next_sibling()
                                    p_tag = self.soup.new_tag("p")
                                    p_tag.string = next_tag.text
                                    tag.append(p_tag)
                                    id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                                    p_tag['class'] = next_tag['class']
                                    p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                    count_of_p_tag += 1
                                    ol_tag_for_roman.append(tag)
                                    next_tag.decompose()
                                    next_tag = sub_tag
                                elif re.search('^\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\)', next_tag.text.strip()):
                                    roman_id = re.search('^\((?P<roman_id>(xc|xl|l?x{0,3})(ix|iv|v?i{0,3}))\)',next_tag.text.strip()).group('roman_id')
                                    if roman_id != roman_number:
                                        sub_tag = next_tag.find_next_sibling()
                                        p_tag = self.soup.new_tag("p")
                                        p_tag.string = next_tag.text
                                        tag.append(p_tag)
                                        id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                                        p_tag['class'] = next_tag['class']
                                        p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                        count_of_p_tag += 1
                                        ol_tag_for_roman.append(tag)
                                        next_tag.decompose()
                                        next_tag = sub_tag
                                    else:
                                        break
                                elif re.search("^\([A-Z]\)", next_tag.text.strip()):
                                    alpha_id = re.search("^\((?P<alpha_id>[A-Z])\)", next_tag.text.strip()).group('alpha_id')
                                    if alpha_id != caps_alpha:
                                        sub_tag = next_tag.find_next_sibling()
                                        p_tag = self.soup.new_tag("p")
                                        p_tag.string = next_tag.text
                                        p_tag['class'] = next_tag['class']
                                        tag.append(p_tag)
                                        id_of_last_li=ol_tag_for_roman.find_all("li",class_="roman")[-1].attrs['id']
                                        p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                        count_of_p_tag += 1
                                        p_tag['class'] = next_tag['class']
                                        next_tag.decompose()
                                        ol_tag_for_roman.append(tag)
                                        next_tag = sub_tag
                                    else:
                                        break
                        count_of_p_tag = 1
                        if re.search(f'^\({number}\)', next_tag.text.strip()):
                            if ol_tag_for_caps_alphabet.li:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_roman)
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                    ol_tag_for_caps_alphabet)
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                            elif ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.find_all("li",class_="inner_alpha")[-1].append(ol_tag_for_roman)
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                                ol_tag_for_inner_alphabet=self.soup.new_tag("ol",type="a")
                                inner_alphabet="a"
                            elif ol_tag_for_number.li:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                        elif re.search(f'^\({roman_number}\)',next_tag.text.strip()) and ol_tag_for_number.li:
                            continue
                        elif re.search(f'^\({alphabet}{alphabet}?\)', next_tag.text.strip()) and alphabet!="a":
                            if ol_tag_for_number.li:  # a 1 i
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                    ol_tag_for_number)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                            elif ol_tag_for_alphabet.li:  # a i
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                    ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                        elif re.search(f'^\({inner_alphabet}\)',next_tag.text.strip()):

                            ol_tag_for_inner_alphabet.find_all("li",class_="inner_alpha")[-1].append(ol_tag_for_roman)
                            ol_tag_for_roman=self.soup.new_tag("ol",type="i")
                            roman_number="i"
                        elif next_tag.name == "h4":
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.find_all("li",class_="inner_alpha")[-1].append(ol_tag_for_roman)
                                if ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                    ol_tag_for_inner_alphabet=self.soup.new_tag("ol",type="a")
                                    inner_alphabet="a"
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                            elif ol_tag_for_number.li:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                if ol_tag_for_alphabet.li:
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                    alphabet = "a"
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                            elif ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_roman)
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = "a"

                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                            roman_number = "i"
                elif re.search(f'^\({alphabet}{alphabet}?\)|^\({inner_alphabet}\)', tag.text.strip()):
                    if re.search(f'^\({alphabet}\) \({number}\)', tag.text.strip()):
                        if re.search(f'^\({alphabet}\) \({number}\) \({roman_number}\)', tag.text.strip()):
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                f'^<li[^>]*>(<span.*</span>)?<b>\({alphabet}\) \({number}\) \({roman_number}\)</b>|^<li[^>]*>(<span.*</span>)?\({alphabet}\) \({number}\) \({roman_number}\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_roman)
                            li_tag_for_alphabet = self.soup.new_tag("li")
                            li_tag_for_alphabet['id'] = f"{h3_id}ol{ol_count}{alphabet}"
                            li_tag_for_alphabet['class'] = "alphabet"
                            li_tag_for_number=self.soup.new_tag("li")
                            li_tag_for_number['id']=f"{h3_id}ol{ol_count}{alphabet}{number}"
                            li_tag_for_number['class']="number"
                            li_tag_for_number.append(ol_tag_for_roman)
                            ol_tag_for_number.append(li_tag_for_number)
                            li_tag_for_alphabet.append(ol_tag_for_number)
                            ol_tag_for_alphabet.append(li_tag_for_alphabet)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}{roman_number}"
                            tag['class'] = "roman"
                            number += 1
                            alphabet = chr(ord(alphabet) + 1)
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            while re.search("^[a-z A-Z]+", next_tag.text.strip()) and next_tag.name!="h4":
                                sub_tag = next_tag.find_next_sibling()
                                p_tag = self.soup.new_tag("p")
                                p_tag.string = next_tag.text
                                p_tag['id'] = f"{tag['id']}.{count_of_p_tag}"
                                count_of_p_tag += 1
                                p_tag['class'] = next_tag['class']
                                tag.append(p_tag)
                                next_tag.decompose()
                                next_tag = sub_tag
                            count_of_p_tag = 1
                        else:
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                f'^<li[^>]*>(<span.*</span>)?<b>\({alphabet}\)( \({number}\))?</b>( \(\d+\))?|^<li[^>]*>(<span.*</span>)?\({alphabet}\) \({number}\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_number)
                            li_tag = self.soup.new_tag("li")
                            li_tag['id'] = f"{h3_id}ol{ol_count}{alphabet}"
                            li_tag['class'] = "alphabet"
                            ol_tag_for_number.wrap(li_tag)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}"
                            tag['class'] = "number"
                            li_tag.wrap(ol_tag_for_alphabet)
                            number += 1
                            alphabet = chr(ord(alphabet) + 1)
                            while re.search("^[a-z A-Z]+", next_tag.text.strip()) and next_tag.name!="h4":
                                sub_tag = next_tag.find_next_sibling()
                                p_tag = self.soup.new_tag("p")
                                p_tag.string = next_tag.text
                                p_tag['id'] = f"{tag['id']}.{count_of_p_tag}"
                                count_of_p_tag += 1
                                p_tag['class'] = next_tag['class']
                                tag.append(p_tag)
                                next_tag.decompose()
                                next_tag = sub_tag
                            count_of_p_tag = 1
                            if re.search(f'^\({alphabet}{alphabet}?\)', next_tag.text.strip()):
                                ol_tag_for_number=self.soup.new_tag("ol")
                                number=1
                    elif re.search(f'^\({alphabet}{alphabet}?\)', tag.text.strip()):
                        alpha_id = re.search(f'^\((?P<alpha_id>{alphabet}{alphabet}?)\)', tag.text.strip()).group(
                            'alpha_id')
                        tag.name = "li"
                        text = str(tag)
                        tag_string = re.sub(
                            '^<li[^>]*>(<span.*</span>)?<b>\([a-z]+\)</b>|^<li[^>]*>(<span.*</span>)?\([a-z]+\)|</li>$',
                            '', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        if ol_tag_for_number.li:
                            if alpha_id == inner_alphabet:
                                tag.wrap(ol_tag_for_inner_alphabet)
                                number_id = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                                tag.attrs['id'] = f"{number_id}{inner_alphabet}"
                                tag['class'] = "inner_alpha"
                                inner_alphabet = chr(ord(inner_alphabet) + 1)
                                if re.search(f'^\({number}\)', next_tag.text.strip()):
                                    if ol_tag_for_number.li:
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_inner_alphabet)
                                        ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                        inner_alphabet = 'a'
                            else:
                                tag.wrap(ol_tag_for_roman)
                                tag['class'] = "roman"
                                if ol_tag_for_number.li:
                                    id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs[
                                        'id']
                                elif ol_tag_for_alphabet.li:
                                    id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs[
                                        'id']
                                tag['id'] = f"{id_of_last_li}{roman_number}"
                                roman_number = roman.fromRoman(roman_number.upper())
                                roman_number += 1
                                roman_number = roman.toRoman(roman_number).lower()
                                while (re.search('^“?[a-z A-Z]+',next_tag.text.strip()) or (next_tag.next_element and next_tag.next_element.name == "br"))and next_tag.name!="h4":  # 5-31.1-1. after 16i 2 break
                                    if next_tag.next_element.name == "br":
                                        sub_tag = next_tag.find_next_sibling()
                                        next_tag.decompose()
                                        next_tag = sub_tag
                                    elif re.search("^“?[a-z A-Z]+",
                                                   next_tag.text.strip()) and next_tag.name != "h4":
                                        sub_tag = next_tag.find_next_sibling()
                                        p_tag = self.soup.new_tag("p")
                                        p_tag.string = next_tag.text
                                        tag.append(p_tag)
                                        id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs[
                                            'id']
                                        p_tag['class'] = next_tag['class']
                                        p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                        count_of_p_tag += 1
                                        ol_tag_for_roman.append(tag)
                                        next_tag.decompose()
                                        next_tag = sub_tag
                                count_of_p_tag = 1
                                if re.search(f'^\({number}\)', next_tag.text.strip()):
                                    if ol_tag_for_caps_alphabet.li:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_caps_alphabet)
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = 'A'
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = 'i'
                                    elif ol_tag_for_number.li:
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = 'i'
                                elif re.search(f'^\({roman_number}\)', next_tag.text.strip()):
                                    continue
                                elif re.search(f'^\({alphabet}{alphabet}?\)', next_tag.text.strip()) and alphabet!="a":
                                    if ol_tag_for_number.li:  # a 1 i
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_number)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = 'i'
                                        ol_tag_for_number = self.soup.new_tag("ol")
                                        number = 1
                                    elif ol_tag_for_alphabet.li:  # a i
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = 'i'
                        else:
                            if re.search('^Schedule (IX|IV|V?I{0,3})',tag.find_previous_sibling('h4').text.strip()):
                                tag.attrs['id'] = f"{tag.find_previous_sibling('h4',class_='schedule').attrs['id']}ol{ol_count}{alpha_id}"
                            else:
                                tag.attrs['id'] = f"{h3_id}ol{ol_count}{alpha_id}"
                            tag.wrap(ol_tag_for_alphabet)
                            if alphabet == "z":
                                alphabet = 'a'
                            else:
                                alphabet = chr(ord(alphabet) + 1)
                            tag['class'] = "alphabet"
                            while (next_tag.name != "h4" and next_tag.name != "h3" and not re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', next_tag.text.strip(),re.IGNORECASE) and not re.search('^Section \d+', next_tag.text.strip())) and (re.search('^“?[a-z A-Z]+|^\[See .*\]|^\(Name .*\)',next_tag.text.strip()) or (next_tag.next_element and next_tag.next_element.name == "br")):
                                if next_tag.next_element.name == "br":
                                    sub_tag = next_tag.find_next_sibling()
                                    next_tag.decompose()
                                    next_tag = sub_tag
                                else:
                                    sub_tag = next_tag.find_next_sibling()
                                    p_tag = self.soup.new_tag("p")
                                    count_of_p_tag += 1
                                    p_tag.string = next_tag.text
                                    tag.append(p_tag)
                                    id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs[
                                        'id']
                                    p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                    p_tag['class'] = next_tag['class']
                                    ol_tag_for_alphabet.append(tag)
                                    next_tag.decompose()
                                    next_tag = sub_tag
                            count_of_p_tag = 1
                            if re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', next_tag.text.strip(),
                                         re.IGNORECASE):  # Article 1
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                                ol_count = 1
                                continue
                            elif re.search('^Section \d+', next_tag.text.strip()):
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                                if re.search('\(a\)|\(\d\)', next_tag.find_next_sibling().text.strip()):
                                    ol_count += 1
                            elif next_tag.name == "h4":
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                    else:
                        if re.search(f'^\({inner_alphabet}\) \({roman_number}\)',tag.text.strip()):
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                f'^<li[^>]*>(<span.*</span>)?<b>\({inner_alphabet}\)( \({roman_number}\))?</b>( \(\d+\))?|^<li[^>]*>(<span.*</span>)?\({inner_alphabet}\) \({roman_number}\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_roman)
                            li_tag = self.soup.new_tag("li")
                            li_tag['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}"
                            li_tag['class'] = "inner_alpha"
                            ol_tag_for_roman.wrap(li_tag)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}{roman_number}"
                            tag['class'] = "roman"
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(li_tag)
                            else:
                                li_tag.wrap(ol_tag_for_inner_alphabet)
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                        else:
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                '^<li[^>]*>(<span.*</span>)?<b>\([a-z]+\)</b>|^<li[^>]*>(<span.*</span>)?\([a-z]+\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.append(tag)
                            else:
                                tag.wrap(ol_tag_for_inner_alphabet)
                            number_id = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                            tag.attrs['id'] = f"{number_id}{inner_alphabet}"
                            tag['class']="inner_alpha"
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                            while (re.search('^“?[a-z A-Z]+',next_tag.text.strip()) or (next_tag.next_element and next_tag.next_element.name == "br")) and next_tag.name!="h4":  # 5-31.1-1. after 16i 2 break
                                if next_tag.next_element.name == "br":
                                    sub_tag = next_tag.find_next_sibling()
                                    next_tag.decompose()
                                    next_tag = sub_tag
                                elif re.search("^“?[a-z A-Z]+",next_tag.text.strip()) and next_tag.name != "h4":
                                    sub_tag = next_tag.find_next_sibling()
                                    p_tag = self.soup.new_tag("p")
                                    p_tag.string = next_tag.text
                                    tag.append(p_tag)
                                    id_of_last_li = ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs['id']
                                    p_tag['class'] = next_tag['class']
                                    p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                    count_of_p_tag += 1
                                    ol_tag_for_inner_alphabet.append(tag)
                                    next_tag.decompose()
                                    next_tag = sub_tag
                            count_of_p_tag = 1
                            if re.search(f'^\({number}\)', next_tag.text.strip()):
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li",class_="roman")[-1].append(ol_tag_for_inner_alphabet)
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                    inner_alphabet = 'a'
                                    ol_tag_for_roman=self.soup.new_tag("ol",type="i")
                                    roman_number="i"
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                    ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                    inner_alphabet = 'a'
                            elif re.search(f'^\({caps_roman}\)', next_tag.text.strip()):
                                ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].append(
                                    ol_tag_for_inner_alphabet)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = "a"
                            elif re.search(f'^\({caps_alpha}\)', next_tag.text.strip()):
                                ol_tag_for_inner_number.find_all("li",class_="inner_num")[-1].append(ol_tag_for_inner_alphabet)
                                ol_tag_for_caps_alphabet.find_all("li",class_="caps_alpha")[-1].append(ol_tag_for_inner_number)
                                ol_tag_for_inner_alphabet=self.soup.new_tag("ol",type="a")
                                inner_alphabet="a"
                                ol_tag_for_inner_number=self.soup.new_tag("ol")
                                inner_num=1

                            elif next_tag.name=="h4":
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = 'a'
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                elif re.search(f'^\({number}\)|^\({inner_num}\)', tag.text.strip()):
                    if re.search(f'^\({number}\) \({inner_alphabet}\) \({roman_number}\)',tag.text.strip()):
                        tag.name = "li"
                        text = str(tag)
                        tag_string = re.sub(
                            f'^<li[^>]*>(<span.*</span>)?<b>\({number}\) \({alphabet}\) \({roman_number}\)</b>|^<li[^>]*>(<span.*</span>)?\({number}\) \({alphabet}\) \({roman_number}\)|</li>$',
                            '', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        tag.wrap(ol_tag_for_roman)
                        li_tag_for_number = self.soup.new_tag("li")
                        li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{number}"
                        li_tag_for_number['class'] = "number"
                        li_tag_for_inner_alphabet = self.soup.new_tag("li")
                        li_tag_for_inner_alphabet['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}"
                        li_tag_for_inner_alphabet['class'] = "inner_alpha"
                        li_tag_for_inner_alphabet.append(ol_tag_for_roman)
                        ol_tag_for_inner_alphabet.append(li_tag_for_inner_alphabet)
                        li_tag_for_number.append(ol_tag_for_inner_alphabet)
                        ol_tag_for_number.append(li_tag_for_number)
                        tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}{roman_number}"
                        tag['class'] = "roman"
                        number += 1
                        inner_alphabet = chr(ord(inner_alphabet) + 1)
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                    elif re.search(f'^\({number}\) \({roman_number}\)', tag.text.strip()):
                        if re.search(f'^\({number}\) \({roman_number}\) \({caps_alpha}{caps_alpha}?\)', tag.text.strip()):
                            caps_alpha_id = re.search(f'\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',tag.text.strip()).group('caps_alpha_id')
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\) \((ix|iv|v?i{0,3})\) \([A-Z]\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\) \((ix|iv|v?i{0,3})\) \([A-Z]\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_caps_alphabet)
                            tag['class'] = "caps_alpha"
                            li_tag_for_number = self.soup.new_tag("li")
                            li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{number}"
                            li_tag_for_roman = self.soup.new_tag("li")
                            li_tag_for_roman['id'] = f"{h3_id}ol{ol_count}{number}{roman_number}"
                            li_tag_for_number['class'] = "number"
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{roman_number}-{caps_alpha_id}"
                            li_tag_for_roman['class'] = "roman"
                            li_tag_for_roman.append(ol_tag_for_caps_alphabet)
                            ol_tag_for_roman.append(li_tag_for_roman)
                            li_tag_for_number.append(ol_tag_for_roman)
                            ol_tag_for_number.append(li_tag_for_number)
                            number += 1
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            if caps_alpha=='Z':
                                caps_alpha='A'
                            else:
                                caps_alpha = chr(ord(caps_alpha) + 1)
                        else:
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\) \((ix|iv|v?i{0,3})\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\) \((ix|iv|v?i{0,3})\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_roman)
                            li_tag = self.soup.new_tag("li")
                            li_tag['id'] = f"{h3_id}ol{ol_count}{number}"
                            li_tag['class'] = "number"
                            li_tag.append(ol_tag_for_roman)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{roman_number}"
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            tag['class'] = "roman"
                            ol_tag_for_number.append(li_tag)
                            number += 1
                            while next_tag.name != "h4" and (re.search('^“?[a-z A-Z]+',next_tag.text.strip()) or (next_tag.next_element and next_tag.next_element.name == "br")):  # 5-31.1-1. after 16i 2 break
                                if next_tag.next_element.name == "br":
                                    sub_tag = next_tag.find_next_sibling()
                                    next_tag.decompose()
                                    next_tag = sub_tag
                                elif re.search("^“?[a-z A-Z]+", next_tag.text.strip()):
                                    p_tag = self.soup.new_tag("p")
                                    p_tag.string = next_tag.text
                                    tag.append(p_tag)
                                    id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                                    p_tag['class'] = next_tag['class']
                                    p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                    count_of_p_tag += 1
                                    ol_tag_for_roman.append(tag)
                                    next_tag.decompose()
                                    next_tag = sub_tag
                            count_of_p_tag = 1
                    elif re.search(f'^\({number}\) \({inner_alphabet}\)', tag.text.strip()):
                        if re.search(f'^\({number}\) \({inner_alphabet}\) \({roman_number}\)', tag.text.strip()):
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\) \([a-z]\) \((ix|iv|v?i{0,3})\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\) \([a-z]\) \((ix|iv|v?i{0,3})\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_roman)
                            li_tag_for_number = self.soup.new_tag("li")
                            li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{number}"
                            li_tag_for_number['class'] = "number"
                            li_tag_for_inner_alphabet = self.soup.new_tag("li")
                            li_tag_for_inner_alphabet['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}"
                            li_tag_for_inner_alphabet['class'] = "inner_alpha"
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}{roman_number}"
                            li_tag_for_inner_alphabet.append(ol_tag_for_roman)
                            ol_tag_for_inner_alphabet.append(li_tag_for_inner_alphabet)
                            li_tag_for_number.append(ol_tag_for_inner_alphabet)
                            ol_tag_for_number.append(li_tag_for_number)
                            number += 1
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                        elif re.search(f'^\({number}\) \({inner_alphabet}\)', tag.text.strip()):
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\) \([a-z]\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\) \([a-z]\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_inner_alphabet)
                            li_tag = self.soup.new_tag("li")
                            li_tag['id'] = f"{h3_id}ol{ol_count}{number}"
                            li_tag['class'] = "number"
                            li_tag.append(ol_tag_for_inner_alphabet)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}"
                            tag['class'] = "inner_alpha"
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                            ol_tag_for_number.append(li_tag)
                            number += 1
                            if re.search(f'^\({alphabet}\)', next_tag.text.strip()):
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                                inner_alphabet = 'a'
                    elif re.search(f'^\({number}\) \({caps_alpha}{caps_alpha}?\)', tag.text.strip()):
                        caps_alpha_id = re.search(f'\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',tag.text.strip()).group('caps_alpha_id')
                        tag.name = "li"
                        text = str(tag)
                        tag_string = re.sub(
                            '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\) \([A-Z]\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\) \([A-Z]\)|</li>$',
                            '', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        tag.wrap(ol_tag_for_caps_alphabet)
                        tag['class'] = "caps_alpha"
                        li_tag = self.soup.new_tag("li")
                        li_tag['id'] = f"{h3_id}ol{ol_count}{number}"
                        li_tag['class'] = "number"
                        li_tag.append(ol_tag_for_caps_alphabet)
                        tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}-{caps_alpha_id}"
                        if caps_alpha=='Z':
                            caps_alpha='A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                        ol_tag_for_number.append(li_tag)
                        number += 1
                    elif re.search(f'^\({number}\)',tag.text.strip()) and inner_num==1:
                        tag.name = "li"
                        text = str(tag)
                        tag_string = re.sub(
                            '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\)|</li>$',
                            '', text.strip())
                        tag.clear()
                        tag.append(BeautifulSoup(tag_string, features="html.parser"))
                        tag['class'] = "number"
                        if ol_tag_for_alphabet.li:
                            id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs['id']  # (a) (1)
                            tag['id'] = f"{id_of_last_li}{number}"
                        else:
                            tag['id'] = f"{h3_id}ol{ol_count}{number}"
                        if ol_tag_for_number.li:  # 4-13-1
                            ol_tag_for_number.append(tag)
                        else:
                            tag.wrap(ol_tag_for_number)
                        number += 1
                        while next_tag.name != "h4" and (
                                re.search("^\([A-Z a-z]+\)\.”|^\. \. \.|^“?[a-z A-Z]+|^\([0-9]\)",
                                          next_tag.text.strip()) or (
                                        next_tag.next_element and next_tag.next_element.name == "br")):  # 123 text history of section
                            if next_tag.next_element.name == "br":
                                sub_tag = next_tag.find_next_sibling()
                                next_tag.decompose()
                                next_tag = sub_tag
                            elif re.search("^\([A-Z a-z]+\)\.”|^\. \. \.|^“?[a-z A-Z]+|^\([0-9]\)",
                                           next_tag.text.strip()):
                                if re.search("^\([A-Z a-z]+\)\.”|^\. \. \.|^“?[a-z A-Z]+", next_tag.text.strip()):
                                    sub_tag = next_tag.find_next_sibling()
                                    p_tag = self.soup.new_tag("p")
                                    p_tag.string = next_tag.text
                                    p_tag['class'] = next_tag['class']
                                    tag.append(p_tag)
                                    id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs[
                                        'id']
                                    p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                    count_of_p_tag += 1
                                    ol_tag_for_number.append(tag)
                                    next_tag.decompose()
                                    next_tag = sub_tag
                                elif re.search('^\([0-9]\)', next_tag.text.strip()):
                                    number_id = re.search('^\((?P<number_id>([0-9]))\)', next_tag.text.strip()).group(
                                        'number_id')
                                    if number_id != str(number):
                                        sub_tag = next_tag.find_next_sibling()
                                        p_tag = self.soup.new_tag("p")
                                        p_tag.string = next_tag.text
                                        tag.append(p_tag)
                                        id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs[
                                            'id']
                                        p_tag['class'] = next_tag['class']
                                        p_tag['id'] = f"{id_of_last_li}.{count_of_p_tag}"
                                        count_of_p_tag += 1
                                        ol_tag_for_number.append(tag)
                                        next_tag.decompose()
                                        next_tag = sub_tag
                                    else:
                                        break
                        count_of_p_tag = 1
                        if re.search('^Section \d+', next_tag.text.strip()):
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                            if re.search('^\(a\)|^\(\d\)', next_tag.find_next_sibling().text.strip()):
                                ol_count += 1
                        elif re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', next_tag.text.strip()):
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                            ol_count = 1
                        elif re.search(f'^\({alphabet}\)', next_tag.text.strip()) and not re.search('^\(ii\)', next_tag.find_next_sibling().text.strip()):
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                        elif next_tag.name=="h4":
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                    elif re.search(f'^\({inner_num}\)', tag.text.strip()):
                        if re.search(f'^\({inner_num}\) \({inner_roman}\)', tag.text.strip()):
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\) \((ix|iv|v?i{0,3})\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\) \((ix|iv|v?i{0,3})\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            tag.wrap(ol_tag_for_inner_roman)
                            li_tag = self.soup.new_tag("li")
                            if ol_tag_for_caps_alphabet.li:
                                id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                            elif ol_tag_for_inner_alphabet.li:
                                id_of_last_li = ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs['id']
                                # (a) (1)
                            elif ol_tag_for_number.li:
                                id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                            li_tag['id'] = f"{id_of_last_li}{inner_num}"
                            li_tag['class'] = "inner_num"
                            li_tag.append(ol_tag_for_inner_roman)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{inner_num}{inner_roman}"
                            inner_roman = roman.fromRoman(inner_roman.upper())
                            inner_roman += 1
                            inner_roman = roman.toRoman(inner_roman).lower()
                            ol_tag_for_inner_number.append(li_tag)
                            inner_num += 1
                        else:
                            tag.name = "li"
                            text = str(tag)
                            tag_string = re.sub(
                                '^<li[^>]*>(<span.*</span>)?<b>\(\d{1,2}\)</b>|^<li[^>]*>(<span.*</span>)?\(\d{1,2}\)|</li>$',
                                '', text.strip())
                            tag.clear()
                            tag.append(BeautifulSoup(tag_string, features="html.parser"))
                            if ol_tag_for_caps_alphabet.li:
                                id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                                # (a) (1)
                            elif ol_tag_for_roman.li:
                                id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                            elif ol_tag_for_inner_alphabet.li:
                                id_of_last_li = ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs['id']
                            elif ol_tag_for_number.li:
                                id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                            tag['id'] = f"{id_of_last_li}{inner_num}"
                            tag['class'] = "inner_num"
                            ol_tag_for_inner_number.append(tag)
                            inner_num += 1
                            if re.search(f'^\({roman_number}\)', next_tag.text.strip()):  # roman i
                                if ol_tag_for_caps_alphabet.li:
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_inner_number)
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type='A')
                                    caps_alpha = 'A'
                                else:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_inner_number)
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                            elif re.search(f'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()):
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_inner_number)
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1
                            elif re.search(f'^\({inner_alphabet}\)', next_tag.text.strip()):
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li",class_="roman")[-1].append(ol_tag_for_inner_number)
                                    ol_tag_for_inner_alphabet.find_all("li",class_="inner_alpha")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_roman=self.soup.new_tag("ol",type="i")
                                    roman_number="i"
                                else:
                                    ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(ol_tag_for_inner_number)
                                ol_tag_for_inner_number=self.soup.new_tag("ol")
                                inner_num=1
        print('ol created')

    def create_div_tag(self):
        div_tag_for_chapter = self.soup.new_tag("div")
        div_tag_for_section = self.soup.new_tag("div")
        div_tag_for_h4 = self.soup.new_tag("div")
        div_tag_for_h5 = self.soup.new_tag("div")
        div_tag_for_article = self.soup.new_tag("div")
        div_tag_for_part = self.soup.new_tag("div")
        for tag in self.soup.find_all("h2"):
            if re.search('^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?', tag.text.strip()):
                next_tag = tag.find_next_sibling()
                tag.wrap(div_tag_for_chapter)
                if next_tag.name == "nav":
                    sibling_of_nav = next_tag.find_next_sibling()
                    div_tag_for_chapter.append(next_tag)
                    next_tag = sibling_of_nav
                    if next_tag.name == "h4":
                        sibling_of_h4 = next_tag.find_next_sibling()
                        div_tag_for_h4.append(next_tag)
                        next_tag = sibling_of_h4
                        while next_tag.name == "p":
                            sibling_of_p = next_tag.find_next_sibling()
                            div_tag_for_h4.append(next_tag)
                            next_tag = sibling_of_p
                        div_tag_for_chapter.append(div_tag_for_h4)
                        div_tag_for_h4 = self.soup.new_tag("div")
                    elif next_tag.name == "h2":
                        sibling_of_h2 = next_tag.find_next_sibling()
                        div_tag_for_part.append(next_tag)
                        next_tag = sibling_of_h2
                        if next_tag.name == "nav":
                            sibling_of_nav = next_tag.find_next_sibling()
                            div_tag_for_part.append(next_tag)
                            next_tag = sibling_of_nav
                    if next_tag.name == "h3":
                        tag_of_h3 = next_tag.find_next_sibling()
                        if re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})', next_tag.text.strip()):
                            next_tag.wrap(div_tag_for_article)
                        else:
                            next_tag.wrap(div_tag_for_section)
                        while tag_of_h3 and (tag_of_h3.name != "h2" or (
                                tag_of_h3.name == "h2" and not re.search('^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                                                         tag_of_h3.text.strip()))):
                            if tag_of_h3.name == "h4":
                                tag_of_h4 = tag_of_h3.find_next_sibling()
                                tag_of_h3.wrap(div_tag_for_h4)
                                while tag_of_h4 and tag_of_h4.name != "h4" and (tag_of_h4.name != "h2" or (
                                        tag_of_h4.name == "h2" and not re.search('^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                                                                 tag_of_h4.text.strip()))):
                                    if tag_of_h4.name == "h2":
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_section.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                            if div_tag_for_part.next_element:
                                                next_tag = tag_of_h4.find_next_sibling()
                                                div_tag_for_part.append(div_tag_for_section)
                                                div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_chapter.append(div_tag_for_part)
                                                div_tag_for_part = self.soup.new_tag("div")
                                                div_tag_for_part.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_part.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                    if tag_of_h4.name == "h3":
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_section.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                        if re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})',
                                                     tag_of_h4.text.strip()):
                                            next_tag = tag_of_h4.find_next_sibling()
                                            tag_of_h4.wrap(div_tag_for_article)
                                            tag_of_h4 = next_tag
                                            while tag_of_h4.name == "p" or tag_of_h4.name == "h3" or tag_of_h4.name=="ol":
                                                if tag_of_h4.name == "h3" and re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})',
                                                        tag_of_h4.text.strip()):
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_section.append(div_tag_for_article)
                                                    div_tag_for_article = self.soup.new_tag("div")
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif tag_of_h4.next_element.name=="br":
                                                    next_tag=tag_of_h4.find_next_sibling()
                                                    tag_of_h4=next_tag
                                                elif tag_of_h4.name=="ol":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif tag_of_h4['class'][0] == self.dictionary_to_store_class_name['History'] :
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif re.search('^[A-Z a-z $ 0-9]+',tag_of_h4.text.strip()) and tag_of_h4.name=="p":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif tag_of_h4['class'][0] == self.dictionary_to_store_class_name['h4']:
                                                    div_tag_for_section.append(div_tag_for_article)
                                                    div_tag_for_article = self.soup.new_tag("div")
                                                    break
                                            div_tag_for_section.append(div_tag_for_article)
                                            div_tag_for_article = self.soup.new_tag("div")
                                        else:  # 2-13-1
                                            if div_tag_for_section.next_element:
                                                if div_tag_for_part.next_element:
                                                    div_tag_for_part.append(div_tag_for_section)
                                                else:
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                            div_tag_for_section = self.soup.new_tag("div")
                                            next_tag = tag_of_h4.find_next_sibling()
                                            div_tag_for_section.append(tag_of_h4)
                                            print(tag_of_h4)
                                            tag_of_h4 = next_tag

                                            if tag_of_h4.name == "p":
                                                next_tag = tag_of_h4.find_next_sibling()
                                                div_tag_for_section.append(tag_of_h4)
                                                tag_of_h4 = next_tag

                                    elif tag_of_h4.name == "h5":
                                        tag_of_h5 = tag_of_h4.find_next_sibling()
                                        tag_of_h4.wrap(div_tag_for_h5)
                                        while tag_of_h5.name != "h5" and tag_of_h5.name != "h3":
                                            if tag_of_h5.next_element.name == "br":
                                                next_tag = tag_of_h5.find_next_sibling()
                                                div_tag_for_h4.append(div_tag_for_h5)
                                                div_tag_for_h5 = self.soup.new_tag("div")
                                                div_tag_for_section.append(div_tag_for_h4)
                                                div_tag_for_h4 = self.soup.new_tag("div")
                                                div_tag_for_section.append(tag_of_h5)
                                                tag_of_h5 = next_tag
                                            elif tag_of_h5.name == "h4":
                                                div_tag_for_h4.append(div_tag_for_h5)
                                                div_tag_for_h5 = self.soup.new_tag("div")
                                                div_tag_for_section.append(div_tag_for_h4)
                                                div_tag_for_h4 = self.soup.new_tag("div")
                                                break
                                            elif tag_of_h5.name == "h2" and re.search('^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                                                                      tag_of_h5.text.strip()):
                                                if div_tag_for_part.next_element:
                                                    div_tag_for_part.append(div_tag_for_section)
                                                    div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                else:
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                                div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_chapter = self.soup.new_tag("div")
                                                break
                                            elif tag_of_h5.name == "h2":
                                                next_tag = tag_of_h5.find_next_sibling()
                                                if div_tag_for_part.next_element:
                                                    div_tag_for_part.append(div_tag_for_section)
                                                    div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                    div_tag_for_part.append(tag_of_h5)
                                                    tag_of_h5 = next_tag
                                                    if tag_of_h5.name == "nav":
                                                        next_tag = tag_of_h5.find_next_sibling()
                                                        div_tag_for_part.append(tag_of_h5)
                                                        tag_of_h5 = next_tag
                                                        if tag_of_h5.name == "h3":
                                                            next_tag = tag_of_h5.find_next_sibling()
                                                            div_tag_for_section.append(tag_of_h5)
                                                            tag_of_h5 = next_tag
                                            else:
                                                next_tag = tag_of_h5.find_next_sibling()
                                                div_tag_for_h5.append(tag_of_h5)
                                                tag_of_h5 = next_tag
                                        if div_tag_for_h5.next_element:
                                            div_tag_for_h4.append(div_tag_for_h5)
                                        div_tag_for_h5 = self.soup.new_tag("div")
                                        tag_of_h4 = tag_of_h5
                                    elif tag_of_h4.next_element.name == "br":
                                        next_tag = tag_of_h4.find_next_sibling()
                                        div_tag_for_section.append(div_tag_for_h4)
                                        div_tag_for_h4 = self.soup.new_tag("div")
                                        div_tag_for_section.append(tag_of_h4)
                                        tag_of_h4 = next_tag

                                        if tag_of_h4.name == "h2" and re.search('^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                                                                tag_of_h4.text.strip()):
                                            if div_tag_for_part.next_element:
                                                div_tag_for_part.append(div_tag_for_section)
                                                div_tag_for_chapter.append(div_tag_for_part)
                                                div_tag_for_part = self.soup.new_tag("div")
                                            else:
                                                div_tag_for_chapter.append(div_tag_for_section)
                                            div_tag_for_section = self.soup.new_tag("div")
                                            div_tag_for_chapter = self.soup.new_tag("div")
                                        elif tag_of_h4.name == "h2":
                                            if div_tag_for_part.next_element:
                                                next_tag = tag_of_h4.find_next_sibling()
                                                div_tag_for_part.append(div_tag_for_section)
                                                div_tag_for_chapter.append(div_tag_for_part)
                                                div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_part = self.soup.new_tag("div")
                                                div_tag_for_part.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_part.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                    if tag_of_h4.name == "h3":
                                                        next_tag = tag_of_h4.find_next_sibling()
                                                        div_tag_for_section.append(tag_of_h4)
                                                        tag_of_h4 = next_tag

                                    elif tag_of_h4.name == "nav":
                                        next_tag = tag_of_h4.find_next_sibling()
                                        div_tag_for_h4.append(tag_of_h4)
                                        tag_of_h4 = next_tag
                                    elif tag_of_h4.name == "ol":
                                        next_tag = tag_of_h4.find_next_sibling()
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_h4.append(tag_of_h4)
                                        else:
                                            div_tag_for_section.append(tag_of_h4)
                                        tag_of_h4 = next_tag
                                    elif tag_of_h4.name == "p":
                                        next_tag = tag_of_h4.find_next_sibling()
                                        if tag_of_h4.text.isupper():  # after article caps title
                                            if div_tag_for_h4.next_element:
                                                div_tag_for_section.append(div_tag_for_h4)
                                                div_tag_for_h4 = self.soup.new_tag("div")
                                            div_tag_for_section.append(tag_of_h4)
                                        else:
                                            if div_tag_for_h4.next_element:
                                                div_tag_for_h4.append(tag_of_h4)
                                            else:
                                                div_tag_for_section.append(tag_of_h4)
                                        tag_of_h4 = next_tag

                                if div_tag_for_h4.next_element:
                                    div_tag_for_section.append(div_tag_for_h4)
                                    div_tag_for_h4 = self.soup.new_tag("div")

                            elif tag_of_h3.name == "h3" and re.search('^ARTICLE (XC|XL|L?X{0,3})(IX|IV|V?I{0,3})',
                                                                      tag_of_h3.text.strip()):
                                next_tag = tag_of_h3.find_next_sibling()
                                div_tag_for_article.append(tag_of_h3)
                                tag_of_h3 = next_tag
                                # chapter 24
                                while tag_of_h3.name != "h3" and tag_of_h3.name != "h4":
                                    next_tag = tag_of_h3.find_next_sibling()
                                    div_tag_for_article.append(tag_of_h3)
                                    tag_of_h3 = next_tag
                                div_tag_for_section.append(div_tag_for_article)
                                div_tag_for_article = self.soup.new_tag("div")
                            else:
                                next_tag = tag_of_h3.find_next_sibling()
                                div_tag_for_section.append(tag_of_h3)
                            tag_of_h3 = next_tag

                        if div_tag_for_section.next_element:
                            if div_tag_for_part.next_element:
                                div_tag_for_part.append(div_tag_for_section)
                                div_tag_for_chapter.append(div_tag_for_part)
                                div_tag_for_part = self.soup.new_tag('div')
                            else:
                                div_tag_for_chapter.append(div_tag_for_section)
                            div_tag_for_section = self.soup.new_tag("div")
                            div_tag_for_part = self.soup.new_tag("div")
                            div_tag_for_chapter = self.soup.new_tag("div")

    def remove_class_name(self):
        for tag in self.soup.find_all():
            if tag.name not in ["ul", "li", "h2", "p", "cite"]:
                del tag['class']
            if tag.name in ["ul", "h2", "p", "li"]:
                if tag['class'] not in ["chapter", "leaders", "transformation", "nav_li", "notes_section"]:
                    del tag['class']

    def remove_from_head(self):
        list_to_remove_from_head = ['text/css', 'LEXIS Publishing']
        for tag in self.soup.find_all('meta'):
            if tag['content'] in list_to_remove_from_head:
                tag.decompose()
        meta_tag = self.soup.find('meta', attrs={'name': 'Description'})
        meta_tag.decompose()
        style_tag = self.soup.find('style')
        style_tag.decompose()

    def adding_css_to_file(self):
        head_tag = self.soup.find("head")
        link_tag = self.soup.new_tag("link", rel="stylesheet",
                                     href="https://unicourt.github.io/cic-code-ga/transforms/ga/stylesheet/ga_code_stylesheet.css")
        head_tag.append(link_tag)

    def add_watermark(self):
        meta_tag = self.soup.new_tag('meta')
        meta_tag_for_water_mark = self.soup.new_tag('meta')
        meta_tag['content'] = "width=device-width, initial-scale=1"
        meta_tag['name'] = "viewport"
        meta_tag_for_water_mark.attrs['name'] = "description"
        meta_tag_for_water_mark.attrs[
            'content'] = f"Release {self.release_number} of the Official Code of Rhode Island Annotated released 2021.11.Transformed and posted by Public.Resource.Org using rtf-parser.py version 1.0 on 2022-06-13.This document is not subject to copyright and is in the public domain."
        self.soup.head.append(meta_tag)
        self.soup.head.append(meta_tag_for_water_mark)

    def cleanup(self):
        for tag in self.soup.find_all(["p", "span"]):
            if not tag.text:
                tag.decompose()

    def write_to_file(self):
        soup_text = str(self.soup.prettify())
        soup_text = soup_text.replace('/>', ' />')
        soup_text = re.sub('&(!?amp;)', '&amp;', soup_text)
        with open(f"../../cic-code-ri/transforms/ri/ocri/r{self.release_number}/{self.html_file}", "w") as file:
            file.write(soup_text)
        file.close()

    def start_parse(self):
        """
             - set the values to instance variables
             - check if the file is constitution file or title file
             - based on file passed call the methods to parse the passed htmls
         """
        self.release_label = f'Release-{self.release_number}'
        start_time = datetime.now()
        print(start_time)
        self.create_soup()
        if re.search('constitution', self.html_file):
            # self.class_regex = {
            #     'head1': r'^The Constitution of the State|^CONSTITUTION OF THE UNITED STATES OF AMERICA',
            #     'ul': r'^Preamble', 'head2': '^Article I',
            #     'head4': '^Notes to Decisions', 'junk1': '^Text$',
            #     'head3': r'^Section \d\.|^§ \d\.', 'NTD': '^Analysis'}
            # self.generate_class_name()
            # self.remove_junk()
            # self.replace_tags()
            # self.create_chapter_section_nav()
            # self.convert_paragraph_to_alphabetical_ol_tags()
            # self.create_Notes_to_Decisions_con()
            # self.create_Notes_to_Decisions_ul_con()
            pass
        else:
            self.get_class_name()
            self.remove_junk()
            self.convert_to_header_and_assign_id()
            self.create_nav_and_ul_tag()
            self.add_citation()
            self.create_nav_and_main_tag()
            self.create_ol_tag()
            self.create_div_tag()
            self.remove_class_name()
            self.remove_from_head()
            self.adding_css_to_file()
            self.add_watermark()
            self.cleanup()
            self.write_to_file()
        print(f'finished {self.html_file}')
        print(datetime.now() - start_time)

