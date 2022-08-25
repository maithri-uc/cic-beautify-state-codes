import re
import roman
from bs4 import BeautifulSoup, Doctype
from os.path import exists
from parser_base import ParserBase
from datetime import datetime


class RIParseHtml(ParserBase):
    def __init__(self, input_file_name):
        super().__init__()
        self.html_file = input_file_name
        self.soup = None
        self.list_store_anchor_reference = []
        self.list_to_store_id = []
        self.title = None
        self.dictionary_to_store_class_name = {'h1': r'^Title \d+[A-Z]?(\.\d+)?', 'h4': r'Compiler’s Notes\.|Repealed Sections\.',
                                               'History': r'History of Section\.',
                                               'li': r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                               'h3': r'^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?|^Chs\.\s*\d+\s*-\s*\d+\.',
                                               'h2': r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                               'junk': '^Text|^Annotations', 'ol_of_i': r'\([A-Z a-z]\)'}
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
                lambda tag: tag.name == 'p' and re.search(self.dictionary_to_store_class_name[key],
                                                          tag.text.strip()) and tag.attrs['class'][
                                0] not in self.dictionary_to_store_class_name.values())
            if tag_class:
                class_name = tag_class['class'][0]
                self.dictionary_to_store_class_name[key] = class_name
        print(self.dictionary_to_store_class_name)

    def remove_junk(self):
        for tag in self.soup.find_all("p", string=re.compile('Annotations|Text|History')):
            class_name = tag['class'][0]
            if class_name == self.dictionary_to_store_class_name['junk']:
                tag.decompose()
        if title := re.search(r'^Title (?P<title>\d+[A-Z]?(\.\d+)?)', self.soup.find('p', class_=self.dictionary_to_store_class_name['h1']).get_text()):
            self.title = title.group('title')
        else:
            self.title = 'constitution-{0}'.format(re.search(r"\.(?P<title>\w+)\.html", self.html_file).group("title"))

    def recreate_tag(self, tag):
        new_tag = self.soup.new_tag("p")
        text = tag.b.text
        new_tag.string = text
        new_tag['class'] = tag['class']
        tag.insert_before(new_tag)
        tag.string = re.sub(f'{text}', '', tag.text.strip())
        return tag, new_tag

    def convert_to_header_and_assign_id_for_constitution(self):
        list_to_store_regex_for_h4 = ['Compiler’s Notes.', 'Compiler\'s Notes.', 'Cross References.',
                                      'Definitional Cross References.',
                                      'Comparative Legislation.',
                                      'Collateral References.', 'NOTES TO DECISIONS', 'Comparative Provisions.',
                                      'Repealed Sections.', 'Effective Dates.', 'Law Reviews.', 'Rules of Court.',
                                      'OFFICIAL COMMENT', 'Official Comment.', 'Official Comments', 'Comment.',
                                      'COMMISSIONER’S COMMENT', 'History of Amendment.']
        count_for_duplicate = 0
        counter_for_cross_reference = 0

        for tag in self.soup.find_all("p"):
            class_name = tag['class'][0]
            if class_name == self.dictionary_to_store_class_name['h1']:
                tag.name = "h1"
                if re.search("^Constitution of the State|^CONSTITUTION OF THE UNITED STATES", tag.text.strip()):
                    match = re.search("^Constitution of the State|^CONSTITUTION OF THE UNITED STATES",
                                      tag.text.strip()).group()
                    title_id = re.sub(' ', '', match)
                    tag.attrs['id'] = f"t{title_id}"
                else:
                    raise Exception('Title Not found...')
            elif class_name == self.dictionary_to_store_class_name['h2']:
                if re.search("^Article [IVXCL]+", tag.text.strip()):
                    tag.name = "h2"
                    match = re.search("^Article [IVXCL]+", tag.text.strip()).group()
                    chapter_id = re.sub(' ', '', match)
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h1').attrs['id']}-{chapter_id}"
                    tag.attrs['class'] = "chapter"
                elif re.search('^Articles of Amendment', tag.text.strip()):
                    tag.name = "h2"
                    match = re.search('^Articles of Amendment', tag.text.strip()).group()
                    article_id = re.sub(' ', '', match)
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h1').attrs['id']}-{article_id}"
                    tag['class'] = "articles_of_amendment"
                elif re.search('^Amendment [IVXCL]+', tag.text.strip()):
                    tag.name = "h3"
                    match = re.search('^Amendment (?P<amd_id>[IVXCL]+)',
                                      tag.text.strip()).group('amd_id')
                    tag.attrs[
                        'id'] = f"{tag.find_previous_sibling('h2', class_='articles_of_amendment').attrs['id']}-am{match}"
                    tag['class'] = "amendment"
                    self.list_to_store_id.append(tag.attrs['id'])
                elif re.search('^Rhode Island Constitution', tag.text.strip()):
                    tag.name = "h3"
                    match = re.search('^Rhode Island Constitution', tag.text.strip()).group()
                    r_id = re.sub('[^A-Za-z0-9]', '', match)
                    tag['id'] = f'{tag.find_previous_sibling("h2").attrs["id"]}-{r_id}'
                    self.list_to_store_id.append(tag.attrs['id'])
                else:
                    raise Exception('header2 pattern Not found...')
            elif class_name == self.dictionary_to_store_class_name['h3']:
                if re.search(r"^§ \d+\.", tag.text.strip()):
                    tag.name = "h3"
                    tag['class'] = "section"
                    match = re.search(r"^§ (?P<section_id>(\d+))\.", tag.text.strip()).group('section_id')
                    tag[
                        'id'] = f"{tag.find_previous_sibling(['h3', 'h2'], ['amendment', 'chapter']).get('id')}s{match.zfill(2)}"
                    self.list_to_store_id.append(tag.attrs['id'])
                elif re.search('^Preamble', tag.text.strip()):
                    tag.name = "h2"
                    match = re.search("^Preamble", tag.text.strip()).group()
                    chapter_id = re.sub('[^A-Za-z0-9]', '', match)
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h1').attrs['id']}-{chapter_id}"
                    tag.attrs['class'] = "chapter"
                else:
                    raise Exception('section pattern not found...')
            elif class_name == self.dictionary_to_store_class_name['History'] or class_name == self.dictionary_to_store_class_name['ol_of_i']:
                if re.search(r"^History of Section\.", tag.text.strip()):
                    tag, new_tag = self.recreate_tag(tag)
                    new_tag.name = "h4"
                    sub_section_id = re.sub(r'[^a-zA-Z0-9]', '', new_tag.text.strip()).lower()
                    new_tag.attrs['id'] = f"{new_tag.find_previous_sibling(['h3', 'h2']).get('id')}-{sub_section_id}"
                else:
                    if tag.text.strip() in list_to_store_regex_for_h4:
                        tag.name = "h4"
                        h4_id = f"{tag.find_previous_sibling(['h3', 'h2']).get('id')}-{re.sub(r'[^a-zA-Z0-9]', '', tag.text).lower()}"
                        if self.soup.find("h4", id=h4_id):
                            counter_for_cross_reference += 1
                            tag[
                                'id'] = f"{tag.find_previous_sibling(['h3', 'h2']).get('id')}-{re.sub(r'[^a-zA-Z0-9]', '', tag.text).lower()}.{str(counter_for_cross_reference).zfill(2)}"
                        else:
                            tag[
                                'id'] = f"{tag.find_previous_sibling(['h3', 'h2']).get('id')}-{re.sub(r'[^a-zA-Z0-9]', '', tag.text).lower()}"
                            counter_for_cross_reference = 0
                        if tag.text.strip() == 'NOTES TO DECISIONS':
                            tag_id = tag.attrs['id']
                            for sub_tag in tag.find_next_siblings():

                                class_name = sub_tag.attrs['class'][0]
                                if class_name == self.dictionary_to_store_class_name['ol_of_i'] and not re.search(
                                        '^Click to view', sub_tag.text.strip()):
                                    sub_tag.name = 'li'
                                elif class_name == self.dictionary_to_store_class_name[
                                    'History'] and sub_tag.b and re.search(r'Collateral References\.',
                                                                           sub_tag.text) is None:
                                    sub_tag.name = "h5"
                                    sub_tag_id = re.sub(r'[^a-zA-Z0-9]', '', sub_tag.text.strip()).lower()
                                    if re.search('^—(?! —)', sub_tag.text.strip()):
                                        sub_tag.attrs[
                                            'id'] = f"{sub_tag.find_previous_sibling('h5', class_='notes_section').attrs['id']}-{sub_tag_id}"
                                        sub_tag['class'] = "notes_sub_section"

                                    elif re.search('^— —', sub_tag.text.strip()):
                                        sub_tag.attrs[
                                            'id'] = f"{sub_tag.find_previous_sibling('h5', class_='notes_sub_section').attrs['id']}-{sub_tag_id}"
                                    else:
                                        h5_id = f"{tag_id}-{sub_tag_id}"
                                        duplicate = self.soup.find_all("h5", id=h5_id)
                                        if len(duplicate):
                                            count_for_duplicate += 1
                                            sub_tag.attrs['id'] = f"{h5_id}.{str(count_for_duplicate).zfill(2)}"
                                        else:
                                            count_for_duplicate = 0
                                            sub_tag.attrs['id'] = f"{h5_id}"
                                        sub_tag.attrs['class'] = 'notes_section'
                                elif sub_tag['class'][0] == self.dictionary_to_store_class_name["h2"] or re.search(
                                        r'Collateral References\.', sub_tag.text) or sub_tag['class'][0] == \
                                        self.dictionary_to_store_class_name['h3']:
                                    break
            elif class_name == self.dictionary_to_store_class_name['li']:
                if re.search("^Article [IVXCL]+", tag.text.strip()) or re.search(
                        '^Amendment [IVXCL]+', tag.text.strip()) or re.search('^Rhode Island Constitution', tag.text.strip()) or re.search(r"^§ \d+\.", tag.text.strip()) or re.search('^Preamble', tag.text.strip()) or re.search('^Articles of Amendment', tag.text.strip()):
                    tag.name = "li"
                    tag['class'] = "nav_li"

    def convert_to_header_and_assign_id(self):

        list_to_store_regex_for_h4 = ['Compiler’s Notes.', 'Compiler\'s Notes.', 'Compiler\'s Notes', 'Cross References.', 'Subsequent Reenactments.', 'Abridged Life Tables and Tables of Work Life Expectancies.',
                                      'Definitional Cross References.', 'Contingent Effective Dates.', 'Applicability.',
                                      'Comparative Legislation.', 'Sunset Provision.', 'Liberal Construction.', 'Sunset Provisions.', 'Legislative Findings.', 'Contingently Repealed Sections.', 'Transferred Sections.',
                                      'Collateral References.', 'NOTES TO DECISIONS', 'Retroactive Effective Dates.', 'Legislative Intent.',
                                      'Repealed Sections.', 'Effective Dates.', 'Law Reviews.', 'Rules of Court.',
                                      'OFFICIAL COMMENT', 'Superseded Sections.', 'Repeal of Sunset Provision.', 'Legislative Findings and Intent.', 'Official Comment.', 'Official Comments', 'Repealed and Reenacted Sections.',
                                      'COMMISSIONER’S COMMENT', 'Comment.', 'Ratification.', 'Federal Act References.', 'Reenactments.', 'Severability.', 'Delayed Effective Dates.', 'Delayed Effective Date.', 'Delayed Repealed Sections.']
        count_for_duplicate = 0
        count_for_cross_reference = 0
        for tag in self.soup.find_all("p"):
            class_name = tag['class'][0]

            if class_name == self.dictionary_to_store_class_name['h1']:
                tag.name = "h1"
                if re.search(r"^Title \d+[A-Z]?(\.\d+)?", tag.text.strip()):
                    title_number = re.search(r"^Title (?P<title_number>\d+[A-Z]?(\.\d+)?)", tag.text.strip()).group(
                        'title_number').zfill(2)
                    tag.attrs['id'] = f"t{title_number}"
                else:
                    raise Exception('Title Not found...')
            elif class_name == self.dictionary_to_store_class_name['h2']:
                if re.search(r"^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?", tag.text.strip()):
                    tag.name = "h2"
                    chapter_number = re.search(r"^Chapters? (?P<chapter_number>\d+(\.\d+)?(\.\d+)?([A-Z])?)",
                                               tag.text.strip()).group('chapter_number').zfill(2)
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h1').attrs['id']}c{chapter_number}"
                    tag.attrs['class'] = "chapter"
                elif re.search(r"^Part (\d{1,2}|[IVXCL]+)", tag.text.strip()):
                    tag.name = "h2"
                    part_number = re.search(r"^Part (?P<part_number>\d{1,2}|[IVXCL]+)", tag.text.strip()).group(
                        'part_number').zfill(2)
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h2', ['article', 'chapter']).attrs['id']}p{part_number}"
                    tag['class'] = "part"
                elif re.search('^Subpart [A-Z0-9]', tag.text.strip()):
                    tag.name = "h2"
                    sub_part_number = re.search("^Subpart (?P<sub_part_number>[A-Z0-9])", tag.text.strip()).group(
                        'sub_part_number')
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h2', class_='part').attrs['id']}sp{sub_part_number}"
                    tag['class'] = "sub_part"
                elif re.search(r'^', tag.text.strip()):
                    tag.name = "h2"
                    article_id = re.search(r'^Article (?P<article_id>(\d+|[IVXCL]+))', tag.text.strip()).group(
                        'article_id')
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h2', class_='chapter').attrs['id']}as{article_id}"
                    tag['class'] = "article"
                else:
                    raise Exception('header2 pattern Not found...')
            elif class_name == self.dictionary_to_store_class_name['h3']:
                tag.name = "h3"
                tag['class'] = "section"
                tag.string = tag.text.replace(u'\xa0', u' ')
                tag.string = tag.text.replace(u'\xa0', u' ')
                if re.search(r"^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?|^Chs\.\s*\d+\s*-\s*\d+\.", tag.text.strip()):
                    if re.search(r"^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?", tag.text.strip()):
                        id_of_section = re.search(
                            r"^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?",
                            tag.text.strip()).group()
                    else:
                        match = re.search(r"^Chs\.\s*(?P<section_id>(\d+\s*-\s*\d+))\.", tag.text.strip()).group(
                            'section_id')
                        id_of_section = re.sub('[^A-Za-z0-9]', '', match)
                    section_id = f"{tag.find_previous_sibling('h2').attrs['id']}s{id_of_section}"
                    if section_id in self.list_to_store_id:
                        count_for_duplicate += 1
                        tag.attrs['id'] = f"{section_id}.{str(count_for_duplicate).zfill(2)}"
                    else:
                        count_for_duplicate = 0
                        tag.attrs['id'] = section_id
                    self.list_to_store_id.append(tag.attrs['id'])
                else:
                    raise Exception('section pattern not found...')
            elif class_name == self.dictionary_to_store_class_name['h4']:
                if re.search(r'^Cross References\. [a-zA-Z0-9]+', tag.text.strip()):
                    tag, new_tag = self.recreate_tag(tag)
                    tag = new_tag
                elif re.search(r'^Definitional Cross References\. [a-z A-Z0-9“]+', tag.text.strip()):
                    tag, new_tag = self.recreate_tag(tag)
                    tag = new_tag
                elif re.search(r'^Purposes( of Changes( and New Matter)?)?\. (\d+|\([a-z]\))', tag.text.strip()):
                    tag, new_tag = self.recreate_tag(tag)
                    tag = new_tag
                if tag.text.strip() in list_to_store_regex_for_h4:
                    tag.name = "h4"
                    h4_id = f"{tag.find_previous_sibling(['h3', 'h2'], ['section', 'chapter', 'part', 'sub_part']).get('id')}-{re.sub(r'[^a-zA-Z0-9]', '', tag.text).lower()}"
                    if tag.text.strip() in ['Official Comment.', 'Official Comments', 'Comment.',
                                            'COMMISSIONER’S COMMENT']:
                        tag['class'] = "comment"
                    if self.soup.find("h4", id=h4_id):
                        tag['id'] = f"{h4_id}.{str(count_for_cross_reference).zfill(2)}"
                    else:
                        count_for_cross_reference = 0
                        tag['id'] = f"{h4_id}"

                if tag.text.strip() == 'NOTES TO DECISIONS':
                    tag_id = tag.attrs['id']
                    for sub_tag in tag.find_next_siblings():
                        class_name = sub_tag.attrs['class'][0]
                        if class_name == self.dictionary_to_store_class_name['History']:
                            sub_tag.name = 'li'
                        elif class_name == self.dictionary_to_store_class_name['h4'] and sub_tag.b and re.search(
                                r'Collateral References\.', sub_tag.text) is None:
                            sub_tag.name = "h5"
                            sub_tag_id = re.sub(r'[^a-zA-Z0-9]', '', sub_tag.text.strip()).lower()
                            if re.search('^—(?! —)', sub_tag.text.strip()):
                                sub_tag.attrs[
                                    'id'] = f"{sub_tag.find_previous_sibling('h5', class_='notes_section').attrs['id']}-{sub_tag_id}"
                                sub_tag['class'] = "notes_sub_section"

                            elif re.search('^— —', sub_tag.text.strip()):
                                sub_tag.attrs[
                                    'id'] = f"{sub_tag.find_previous_sibling('h5', class_='notes_sub_section').attrs['id']}-{sub_tag_id}"
                            else:
                                h5_id = f"{tag_id}-{sub_tag_id}"
                                if h5_id in self.list_to_store_id:
                                    count_for_duplicate += 1
                                    sub_tag.attrs['id'] = f"{h5_id}.{str(count_for_duplicate).zfill(2)}"
                                else:
                                    count_for_duplicate = 0
                                    sub_tag.attrs['id'] = f"{h5_id}"
                                self.list_to_store_id.append(sub_tag.attrs['id'])
                                sub_tag.attrs['class'] = 'notes_section'
                        elif sub_tag['class'][0] == self.dictionary_to_store_class_name['h3'] or sub_tag['class'][0] == \
                                self.dictionary_to_store_class_name['h2'] or re.search(r'Collateral References\.',
                                                                                       sub_tag.text):
                            break
            elif class_name == self.dictionary_to_store_class_name['History']:
                if re.search(r"^History of Section\.", tag.text.strip()):
                    tag, new_tag = self.recreate_tag(tag)
                    new_tag.name = "h4"
                    sub_section_id = re.sub(r'[^a-zA-Z0-9]', '', new_tag.text.strip()).lower()
                    new_tag.attrs[
                        'id'] = f"{new_tag.find_previous_sibling(['h3', 'h2'], ['section', 'chapter', 'part', 'sub_part']).get('id')}-{sub_section_id}"
                elif re.search('The Interstate Compact on Juveniles', tag.text.strip()):
                    tag.name = "h4"
                    tag['id'] = f"{tag.find_previous_sibling(['h3', 'h2'], ['section', 'chapter', 'part', 'sub_part']).get('id')}-{re.sub(r'[^a-zA-Z0-9]', '', tag.text).lower()}"
                elif re.search(r"^ARTICLE (\d+|[IVXCL]+)", tag.text.strip(), re.IGNORECASE):
                    if re.search(r"^ARTICLE [IVXCL]+\.?[A-Z a-z]+", tag.text.strip(),
                                 re.IGNORECASE) and tag.name != "li":  # article notes to decision
                        tag, new_tag = self.recreate_tag(tag)
                        new_tag.name = "h3"
                        article_number = re.search('^(ARTICLE (?P<article_id>[IVXCL]+))',
                                                   new_tag.text.strip(), re.IGNORECASE)
                        new_tag.attrs['class'] = 'article_h3'
                        new_tag['id'] = f"{tag.find_previous_sibling('h3', class_='section').attrs['id']}a{article_number.group('article_id')}"

                    elif re.search(r'^Article [IVXCL]+\.', tag.text.strip()):
                        tag.name = 'li'
                    elif re.search(r'^Article \d+\.', tag.text.strip()):
                        tag_for_article = self.soup.new_tag("h3")
                        article_number = re.search(r'^(Article (?P<article_number>\d+)\.)', tag.text.strip())
                        tag_for_article.string = article_number.group()
                        tag_text = tag.text.replace(f'{article_number.group()}', '')
                        tag.insert_before(tag_for_article)
                        tag.clear()
                        tag.string = tag_text
                        tag_for_article.attrs['class'] = 'article_h3'
                        tag_for_article['id'] = f"{tag.find_previous_sibling('h3', class_='section').attrs['id']}a{article_number.group('article_number')}"
                    else:
                        tag.name = "h3"
                        article_id = re.search("^ARTICLE (?P<article_id>[IVXCL]+)", tag.text.strip(), re.IGNORECASE).group('article_id')
                        tag['class'] = 'article_h3'
                        tag['id'] = f"{tag.find_previous_sibling('h3', class_='section').attrs['id']}a{article_id}"
                elif re.search(r"^Section \d+. [a-z ,\-A-Z]+\. \(a\)", tag.text.strip()) and re.search(r"^\(b\)", tag.find_next_sibling().text.strip()):
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
                elif re.search('^Schedule [IVX]+', tag.text.strip()):
                    tag.name = "h4"
                    tag['class'] = 'schedule'
                    schedule_id = re.search('^Schedule (?P<schedule_id>[IVX]+)', tag.text.strip()).group('schedule_id')
                    tag.attrs['id'] = f"{tag.find_previous_sibling('h3', class_='section').attrs['id']}sec{schedule_id}"
            elif class_name == self.dictionary_to_store_class_name['li']:
                if re.search(r"^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?", tag.text.strip()) or re.search(
                        r"^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?|^Chs\.\s*\d+\s*-\s*\d+\.",
                        tag.text.strip()) or re.search(r'^Part (\d{1,2}|[IVXCL]+)', tag.text.strip()) or re.search('^Subpart [A-Z0-9]', tag.text.strip()) or re.search(r'^Article (\d+|[IVXCL]+)', tag.text.strip()):
                    tag.name = "li"
                    tag['class'] = "nav_li"

    def create_li_with_anchor(self, li_tag, ref_id, li_type=None, li_count=None):
        li_tag_text = li_tag.text
        li_tag.clear()
        li_tag.append(self.soup.new_tag("a", href='#' + ref_id))
        self.list_store_anchor_reference.append(ref_id)
        li_tag.a.string = li_tag_text
        if li_type:
            li_tag['id'] = f"{ref_id}-{li_type}{str(li_count).zfill(2)}"
        return li_tag

    def create_nav_and_ul_tag_for_constitution(self):
        ul_tag = self.soup.new_tag("ul")
        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")
        ul_tag_for_sub_section = self.soup.new_tag("ul")
        nav_tag = self.soup.new_tag("nav")
        li_count = 0
        count_for_duplicate = 0
        for li_tag in self.soup.find_all("li"):

            if re.search(r'^§ \d+\.|^Rhode Island Constitution|^Amendment [IVXCL]+',
                         li_tag.text.strip()):
                if re.search('^Rhode Island Constitution', li_tag.text.strip()):
                    match = re.search('^Rhode Island Constitution', li_tag.text.strip()).group()
                    r_id = re.sub('[^A-Za-z0-9]', '', match)
                    h3_id = f'{li_tag.find_previous_sibling("h2").attrs["id"]}-{r_id}'
                elif re.search('^Amendment [IVXCL]+', li_tag.text.strip()):
                    match = re.search('^Amendment (?P<match_id>[IVXCL]+)',
                                      li_tag.text.strip()).group('match_id')
                    h3_id = f'{li_tag.find_previous_sibling("h2", class_="articles_of_amendment").attrs["id"]}-am{match}'
                else:
                    match = re.search(r"^§ (?P<section_id>(\d+))\.", li_tag.text.strip()).group('section_id')
                    h3_id = f"{li_tag.find_previous_sibling(['h3', 'h2'], ['amendment', 'chapter']).get('id')}s{match.zfill(2)}"

                if h3_id in self.list_store_anchor_reference:
                    count_for_duplicate += 1
                    id_count = str(count_for_duplicate).zfill(2)
                    h3_id = f"{h3_id}.{id_count}"
                else:
                    count_for_duplicate = 0
                li_count += 1
                li_tag = self.create_li_with_anchor(li_tag, h3_id, "snav", li_count)
                next_tag = li_tag.find_next_sibling()
                ul_tag.attrs['class'] = 'leaders'
                li_tag.wrap(ul_tag)
                if next_tag.name != "li":
                    ul_tag.wrap(nav_tag)
                    ul_tag = self.soup.new_tag("ul")
                    nav_tag = self.soup.new_tag("nav")
                    li_count = 0
            elif re.search('^Article [IVXCL]+|^Preamble|^Articles of Amendment',
                           li_tag.text.strip()):
                h1_id = None
                if re.search('^Article [IVXCL]+', li_tag.text.strip()):
                    match = re.search("^Article [IVXCL]+", li_tag.text.strip()).group()
                    chapter_id = re.sub(' ', '', match)
                    h1_id = f"{li_tag.find_previous_sibling('h1').attrs['id']}-{chapter_id}"
                elif re.search('^Preamble', li_tag.text.strip()):
                    match = re.search("^Preamble", li_tag.text.strip()).group()
                    chapter_id = re.sub(' ', '', match)
                    h1_id = f"{li_tag.find_previous_sibling('h1').attrs['id']}-{chapter_id}"
                elif re.search('^Articles of Amendment', li_tag.text.strip()):
                    match = re.search('^Articles of Amendment', li_tag.text.strip()).group()
                    article_id = re.sub(' ', '', match)
                    h1_id = f"{li_tag.find_previous_sibling('h1').attrs['id']}-{article_id}"
                li_count += 1
                li_tag = self.create_li_with_anchor(li_tag, h1_id, "cnav", li_count)
                ul_tag.attrs['class'] = 'leaders'
                next_tag = li_tag.find_next_sibling()
                li_tag.wrap(ul_tag)
                if next_tag.name != "li":
                    ul_tag = self.soup.new_tag("ul")
                    li_count = 0
            else:
                h4_id = li_tag.find_previous_sibling("h4").attrs['id']
                sub_section_id = re.sub(r'[^a-zA-Z0-9]', '', li_tag.text.strip()).lower()
                if re.search('^—(?! —)', li_tag.text.strip()):
                    id_of_parent = re.sub(r'[^a-zA-Z0-9]', '',
                                          ul_tag.find_all("li", class_="notes_to_decision")[-1].text).lower()
                    h5_id = f"{h4_id}-{id_of_parent}-{sub_section_id}"
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    li_tag['class'] = "notes_sub_section"
                    ul_tag_for_sub_section['class'] = 'leaders'
                    if re.search('^— ?(—)?', li_tag.find_next_sibling().text.strip()):
                        li_tag.wrap(ul_tag_for_sub_section)
                    elif li_tag.find_next_sibling().name != "li":
                        li_tag.wrap(ul_tag_for_sub_section)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                        ul_tag.wrap(nav_tag)
                        ul_tag = self.soup.new_tag("ul")
                        nav_tag = self.soup.new_tag("nav")
                    else:
                        li_tag.wrap(ul_tag_for_sub_section)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                elif re.search('^— —', li_tag.text.strip()):
                    id_of_section = re.sub(r'[^a-zA-Z0-9]', '',
                                           ul_tag.find_all("li", class_="notes_to_decision")[-1].text).lower()
                    id_of_sub_section = re.sub(r'[^a-zA-Z0-9]', '',
                                               ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[
                                                   -1].text).lower()
                    h5_id = f"{h4_id}-{id_of_section}-{id_of_sub_section}-{sub_section_id}"
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    ul_tag_for_sub_section_2.attrs['class'] = 'leaders'
                    if re.search('^— —', li_tag.find_next_sibling().text.strip()):
                        li_tag.wrap(ul_tag_for_sub_section_2)
                    elif li_tag.find_next_sibling().name != "li":
                        li_tag.wrap(ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[-1].append(
                            ul_tag_for_sub_section_2)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                        ul_tag.wrap(nav_tag)
                        ul_tag = self.soup.new_tag("ul")
                        nav_tag = self.soup.new_tag("nav")
                    elif re.search('^—(?! —)', li_tag.find_next_sibling().text.strip()):
                        li_tag.wrap(ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[-1].append(
                            ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")
                    else:
                        li_tag.wrap(ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[-1].append(
                            ul_tag_for_sub_section_2)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                else:
                    h5_id = f"{h4_id}-{sub_section_id}"
                    if h5_id in self.list_store_anchor_reference:
                        count_for_duplicate += 1
                        id_count = str(count_for_duplicate).zfill(2)
                        h5_id = f"{h5_id}.{id_count}"
                    else:
                        count_for_duplicate = 0
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    ul_tag.attrs['class'] = 'leaders'
                    li_tag['class'] = 'notes_to_decision'
                    if li_tag.find_next_sibling().name != "li":
                        li_tag.wrap(ul_tag)
                        ul_tag.wrap(nav_tag)
                        ul_tag = self.soup.new_tag("ul")
                        nav_tag = self.soup.new_tag("nav")
                    else:
                        li_tag.wrap(ul_tag)

    def create_nav_and_ul_tag(self):
        ul_tag = self.soup.new_tag("ul")
        ul_tag_for_sub_section = self.soup.new_tag("ul")
        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")
        li_count = 0
        count_for_duplicate = 0
        nav_tag = self.soup.new_tag("nav")
        for li_tag in self.soup.find_all("li"):
            li_tag.string = li_tag.text.replace(u'\xa0', u' ')
            if re.search(r"^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?", li_tag.text.strip()):
                chapter_number = re.search(r"^Chapters? (?P<chapter_number>\d+(\.\d+)?(\.\d+)?([A-Z])?)",
                                           li_tag.text.strip()).group('chapter_number').zfill(2)
                h1_id = f"{li_tag.find_previous_sibling('h1').attrs['id']}c{chapter_number}"
                li_count += 1
                li_tag = self.create_li_with_anchor(li_tag, h1_id, "cnav", li_count)
                ul_tag.attrs['class'] = 'leaders'
                next_tag = li_tag.find_next_sibling()
                li_tag.wrap(ul_tag)
                if next_tag.name != "li":
                    ul_tag = self.soup.new_tag("ul")
                    li_count = 0
            elif re.search(
                    r"^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?|^Chs\.\s*\d+\s*-\s*\d+\.|^Article (\d+|[IVXCL]+) ",
                    li_tag.text.strip()):
                if re.search(
                        r"^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?",
                        li_tag.text.strip()):
                    section_id = re.search(
                        r"^\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?",
                        li_tag.text.strip()).group()
                    h3_id = f"{li_tag.find_previous_sibling('h2').attrs['id']}s{section_id}"
                elif re.search(r'^Article (\d+|[IVXCL]+) ', li_tag.text.strip()):
                    section_id = re.search(r'^Article (?P<article_id>(\d+|[IVXCL]+))',
                                           li_tag.text.strip()).group('article_id')
                    h3_id = f"{li_tag.find_previous_sibling('h2').attrs['id']}as{section_id}"
                else:
                    match = re.search(r'^Chs\.\s*(?P<section_id>(\d+\s*-\s*\d+))\.', li_tag.text.strip()).group(
                        'section_id')
                    section_id = re.sub('[^A-Za-z0-9]', '', match)
                    h3_id = f"{li_tag.find_previous_sibling('h2').attrs['id']}s{section_id}"
                if h3_id in self.list_store_anchor_reference:
                    count_for_duplicate += 1
                    id_count = str(count_for_duplicate).zfill(2)
                    h3_id = f"{h3_id}.{id_count}"
                else:
                    count_for_duplicate = 0
                li_count += 1
                li_tag = self.create_li_with_anchor(li_tag, h3_id, "snav", li_count)
                next_tag = li_tag.find_next_sibling()
                ul_tag.attrs['class'] = 'leaders'
                li_tag.wrap(ul_tag)
                if next_tag.name != "li":
                    ul_tag.wrap(nav_tag)
                    ul_tag = self.soup.new_tag("ul")
                    nav_tag = self.soup.new_tag("nav")
                    li_count = 0
            elif re.search(r"^Part (\d{1,2}|[IVXCL]+) ", li_tag.text.strip()):
                part_id = re.search(r"^Part (?P<part_number>\d{1,2}|[IVXCL]+)", li_tag.text.strip()).group(
                    'part_number').zfill(2)
                h2_id = li_tag.find_previous_sibling('h2').attrs['id']
                li_count += 1
                li_tag = self.create_li_with_anchor(li_tag, f"{h2_id}p{part_id}", "snav", li_count)
                next_tag = li_tag.find_next_sibling()
                ul_tag.attrs['class'] = 'leaders'
                if next_tag.name != "li":
                    li_tag.wrap(ul_tag)
                    ul_tag.wrap(nav_tag)
                    ul_tag = self.soup.new_tag("ul")
                    nav_tag = self.soup.new_tag("nav")
                    li_count = 0
                else:
                    li_tag.wrap(ul_tag)
            elif re.search('^Subpart [A-Z0-9]', li_tag.text.strip()):
                sub_part_id = re.search("^Subpart (?P<sub_part_number>[A-Z0-9])", li_tag.text.strip()).group(
                    'sub_part_number')
                h2_id = li_tag.find_previous_sibling('h2').attrs['id']
                li_count += 1
                li_tag = self.create_li_with_anchor(li_tag, f"{h2_id}sp{sub_part_id}", "snav", li_count)
                next_tag = li_tag.find_next_sibling()
                ul_tag.attrs['class'] = 'leaders'
                if next_tag.name != "li":
                    li_tag.wrap(ul_tag)
                    ul_tag.wrap(nav_tag)
                    ul_tag = self.soup.new_tag("ul")
                    nav_tag = self.soup.new_tag("nav")
                    li_count = 0
                else:
                    li_tag.wrap(ul_tag)
            else:
                h4_id = li_tag.find_previous_sibling("h4").attrs['id']
                sub_section_id = re.sub(r'[^a-zA-Z0-9]', '', li_tag.text.strip()).lower()
                if re.search('^—(?! —)', li_tag.text.strip()):
                    id_of_parent = re.sub(r'[^a-zA-Z0-9]', '',
                                          ul_tag.find_all("li", class_="notes_to_decision")[-1].text).lower()
                    h5_id = f"{h4_id}-{id_of_parent}-{sub_section_id}"
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    li_tag['class'] = "notes_sub_section"
                    ul_tag_for_sub_section['class'] = 'leaders'

                    if re.search('^— ?(—)?', li_tag.find_next_sibling().text.strip()):
                        li_tag.wrap(ul_tag_for_sub_section)
                    elif li_tag.find_next_sibling().name != "li":
                        li_tag.wrap(ul_tag_for_sub_section)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                        ul_tag.wrap(nav_tag)
                        ul_tag = self.soup.new_tag("ul")
                        nav_tag = self.soup.new_tag("nav")
                    else:
                        li_tag.wrap(ul_tag_for_sub_section)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                elif re.search('^— —', li_tag.text.strip()):
                    id_of_section = re.sub(r'[^a-zA-Z0-9]', '',
                                           ul_tag.find_all("li", class_="notes_to_decision")[-1].text).lower()
                    id_of_sub_section = re.sub(r'[^a-zA-Z0-9]', '',
                                               ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[
                                                   -1].text).lower()
                    h5_id = f"{h4_id}-{id_of_section}-{id_of_sub_section}-{sub_section_id}"
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    ul_tag_for_sub_section_2.attrs['class'] = 'leaders'
                    if re.search('^— —', li_tag.find_next_sibling().text.strip()):
                        li_tag.wrap(ul_tag_for_sub_section_2)
                    elif li_tag.find_next_sibling().name != "li":
                        li_tag.wrap(ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[-1].append(
                            ul_tag_for_sub_section_2)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                        ul_tag.wrap(nav_tag)
                        ul_tag = self.soup.new_tag("ul")
                        nav_tag = self.soup.new_tag("nav")
                    elif re.search('^—(?! —)', li_tag.find_next_sibling().text.strip()):
                        li_tag.wrap(ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[-1].append(
                            ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")

                    else:
                        li_tag.wrap(ul_tag_for_sub_section_2)
                        ul_tag_for_sub_section.find_all("li", class_="notes_sub_section")[-1].append(
                            ul_tag_for_sub_section_2)
                        ul_tag.find_all("li", class_="notes_to_decision")[-1].append(ul_tag_for_sub_section)
                        ul_tag_for_sub_section_2 = self.soup.new_tag("ul")
                        ul_tag_for_sub_section = self.soup.new_tag("ul")
                else:
                    h5_id = f"{h4_id}-{sub_section_id}"
                    if h5_id in self.list_store_anchor_reference:
                        count_for_duplicate += 1
                        id_count = str(count_for_duplicate).zfill(2)
                        h5_id = f"{h5_id}.{id_count}"
                    else:
                        count_for_duplicate = 0
                    li_tag = self.create_li_with_anchor(li_tag, h5_id)
                    li_tag['class'] = 'notes_to_decision'
                    ul_tag['class'] = 'leaders'
                    if li_tag.find_next_sibling().name != "li":
                        li_tag.wrap(ul_tag)
                        ul_tag.wrap(nav_tag)
                        ul_tag = self.soup.new_tag("ul")
                        nav_tag = self.soup.new_tag("nav")
                    else:
                        li_tag.wrap(ul_tag)

    def create_nav_and_main_tag(self):
        nav_tag_for_header1_and_chapter = self.soup.new_tag("nav")
        p_tag = self.soup.new_tag("p")
        p_tag['class'] = "transformation"
        p_tag.string = f"Release {self.release_number} of the Official Code of Rhode Island Annotated released {self.release_date}. Transformed and posted by Public.Resource.Org using rtf-parser.py version 1.0 on {datetime.now().date()}. This document is not subject to copyright and is in the public domain."
        nav_tag_for_header1_and_chapter.append(p_tag)
        main_tag = self.soup.new_tag("main")
        self.soup.find("h1").wrap(nav_tag_for_header1_and_chapter)
        self.soup.find("ul").wrap(nav_tag_for_header1_and_chapter)
        for tag in nav_tag_for_header1_and_chapter.find_next_siblings():
            tag.wrap(main_tag)

    @staticmethod
    def add_p_tag_to_li(tag, next_tag, count_of_p_tag):
        sub_tag = next_tag.find_next_sibling()
        next_tag['id'] = f"{tag['id']}.{count_of_p_tag}"
        tag.append(next_tag)
        next_tag['class'] = "text"
        count_of_p_tag += 1
        next_tag = sub_tag
        return next_tag, count_of_p_tag

    @staticmethod
    def decompose_break_tag(next_tag):
        sub_tag = next_tag.find_next_sibling()
        next_tag.decompose()
        return sub_tag

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
        ol_tag_for_inner_caps_roman = self.soup.new_tag("ol", type="I")
        inner_caps_roman = 'I'
        count_of_p_tag = 1
        id_of_last_li = None
        for tag in self.soup.main.find_all("p"):
            if not tag.name:
                continue
            class_name = tag['class'][0]
            if class_name == self.dictionary_to_store_class_name['History'] or class_name == \
                    self.dictionary_to_store_class_name['ol_of_i'] or class_name == self.dictionary_to_store_class_name['h4']:
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
                if re.search(fr'^\([gk]\)',
                             tag.text.strip()) and self.html_file == "gov.ri.code.title.19.html" and tag.find_previous_sibling().get(
                        'class') == "h3_part":
                    alphabet = re.search(fr'^\((?P<alpha_id>[gk])\)', tag.text.strip()).group('alpha_id')
                    if alphabet == "g":
                        start = 7
                    else:
                        start = 11
                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a", start=start)
                if re.search(fr'^{number}\.', tag.text.strip()):
                    tag.name = "li"
                    tag.string = re.sub(fr'^{number}\.', '', tag.text.strip())
                    tag['class'] = "number"
                    if ol_tag_for_caps_alphabet.li:
                        tag[
                            'id'] = f"{ol_tag_for_caps_alphabet.find_all('li', class_='caps_alpha')[-1].attrs['id']}{number}"
                    elif ol_tag_for_alphabet.li:
                        tag['id'] = f"{ol_tag_for_alphabet.find_all('li', class_='alphabet')[-1].attrs['id']}{number}"
                    else:
                        tag['id'] = f"{tag.find_previous({'h5', 'h4', 'h3', }).get('id')}ol{ol_count}{number}"
                    tag.wrap(ol_tag_for_number)
                    number += 1
                    while (next_tag.name != "h2" and next_tag.name != "h4" and next_tag.name != "h3") and (
                            re.search('^“?[a-z A-Z]+', next_tag.text.strip()) or next_tag.next_element.name == "br"):
                        if next_tag.next_element.name == "br":
                            next_tag = self.decompose_break_tag(next_tag)
                        elif re.search(fr'^{caps_alpha}{caps_alpha}?\.|^{inner_alphabet}\.', next_tag.text.strip()):
                            break
                        else:
                            next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                    count_of_p_tag = 1
                    if re.search('^ARTICLE [IVXCL]+', next_tag.text.strip()):
                        if ol_tag_for_alphabet.li:
                            ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                            ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                            alphabet = 'a'
                        ol_tag_for_number = self.soup.new_tag("ol")
                        number = 1
                        ol_count = 1
                    elif next_tag.name == "h3" or next_tag.name == "h4" or next_tag.name == "h2":
                        ol_tag_for_number = self.soup.new_tag("ol")
                        number = 1
                    elif re.search(fr'^{caps_alpha}{caps_alpha}?\.|^\({caps_alpha}{caps_alpha}?\)',
                                   next_tag.text.strip()):
                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_number)
                        ol_tag_for_number = self.soup.new_tag("ol")
                        number = 1
                    elif re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()) and ol_tag_for_alphabet.li:
                        if ol_tag_for_caps_alphabet.li:
                            ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_number)
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                            if ol_tag_for_roman.li:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = "i"
                            else:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                    ol_tag_for_caps_alphabet)
                            ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                            caps_alpha = 'A'
                        else:

                            ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                elif re.search(fr'^{caps_alpha}{caps_alpha}?\.', tag.text.strip()):
                    tag.name = "li"
                    tag.string = re.sub(fr'^{caps_alpha}{caps_alpha}?\.', '', tag.text.strip())
                    tag['class'] = "caps_alpha"
                    tag['id'] = f"{tag.find_previous({'h5', 'h4', 'h3'}).get('id')}ol{ol_count}-{caps_alpha}"
                    tag.wrap(ol_tag_for_caps_alphabet)
                    caps_alpha = chr(ord(caps_alpha) + 1)
                    while (next_tag.name != "h2" and next_tag.name != "h4" and next_tag.name != "h3") and (
                            re.search('^“?[a-z A-Z]+', next_tag.text.strip()) or next_tag.next_element.name == "br"):
                        if next_tag.next_element.name == "br":
                            next_tag = self.decompose_break_tag(next_tag)
                        elif re.search(fr'^{caps_alpha}{caps_alpha}?\.', next_tag.text.strip()):
                            break
                        else:
                            next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                    count_of_p_tag = 1
                    if re.search('^ARTICLE [IVXCL]+', next_tag.text.strip()):
                        if ol_tag_for_number.li:
                            ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_number)
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                        caps_alpha = 'A'
                        ol_count = 1
                    elif next_tag.name == "h3" or next_tag.name == "h4" or next_tag.name == "h2":
                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                        caps_alpha = 'A'
                        ol_count = 1
                elif re.search(fr'^{inner_alphabet}\.', tag.text.strip()):
                    tag.name = "li"
                    tag.string = re.sub(fr'^{inner_alphabet}\.', '', tag.text.strip())
                    tag['class'] = "inner_alpha"
                    if ol_tag_for_number.li:
                        tag[
                            'id'] = f'{ol_tag_for_number.find_all("li", class_="number")[-1].attrs["id"]}{inner_alphabet}'
                    tag.wrap(ol_tag_for_inner_alphabet)
                    inner_alphabet = chr(ord(inner_alphabet) + 1)
                    while (next_tag.name != "h2" and next_tag.name != "h4" and next_tag.name != "h3") and (
                            re.search('^“?[a-z A-Z]+', next_tag.text.strip()) or next_tag.next_element.name == "br"):
                        if next_tag.next_element.name == "br":
                            next_tag = self.decompose_break_tag(next_tag)
                        elif re.search(fr'^{alphabet}{alphabet}?\.', next_tag.text.strip()):
                            break
                        else:
                            next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                    count_of_p_tag = 1
                    if re.search(fr'^{number}\.', next_tag.text.strip()):
                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                        ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                        inner_alphabet = 'a'
                    elif next_tag.name == "h3" or next_tag.name == "h4" or next_tag.name == "h2":
                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                        ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                        inner_alphabet = 'a'
                        ol_tag_for_number = self.soup.new_tag("ol")
                        number = 1
                elif re.search(fr'^\({caps_alpha}{caps_alpha}?\)', tag.text.strip()) and caps_roman != 'II':
                    if re.search(fr'^\({caps_alpha}{caps_alpha}?\) \({caps_roman}\)', tag.text.strip()):
                        if re.search(fr'^\({caps_alpha}{caps_alpha}?\) \({caps_roman}\) \({inner_alphabet}\)',
                                     tag.text.strip()):
                            tag.name = "li"
                            caps_alpha_id = re.search(fr'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                      tag.text.strip()).group('caps_alpha_id')
                            tag.string = re.sub(
                                fr'^\({caps_alpha}{caps_alpha}?\) \({caps_roman}\) \({inner_alphabet}\)',
                                '', tag.text.strip())
                            tag.wrap(ol_tag_for_inner_alphabet)
                            li_tag_for_caps_alpha = self.soup.new_tag("li")
                            li_tag_for_caps_alpha[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}"
                            li_tag_for_caps_roman = self.soup.new_tag("li")
                            li_tag_for_caps_roman[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}"
                            li_tag_for_caps_alpha['class'] = "caps_alpha"
                            tag.attrs[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}{inner_alphabet}"
                            tag['class'] = "inner_alpha"
                            li_tag_for_caps_roman['class'] = "caps_roman"
                            li_tag_for_caps_roman.append(ol_tag_for_inner_alphabet)
                            ol_tag_for_caps_roman.append(li_tag_for_caps_roman)
                            li_tag_for_caps_alpha.append(ol_tag_for_caps_roman)
                            ol_tag_for_caps_alphabet.append(li_tag_for_caps_alpha)
                            caps_roman = roman.fromRoman(caps_roman)
                            caps_roman += 1
                            caps_roman = roman.toRoman(caps_roman)
                            if caps_alpha == 'Z':
                                caps_alpha = 'A'
                            else:
                                caps_alpha = chr(ord(caps_alpha) + 1)
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                        else:
                            tag.name = "li"

                            caps_alpha_id = re.search(fr'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                      tag.text.strip()).group('caps_alpha_id')
                            tag.string = re.sub(fr'^\({caps_alpha}{caps_alpha}?\) \({caps_roman}\)', '',
                                                tag.text.strip())
                            tag.wrap(ol_tag_for_caps_roman)
                            li_tag_for_caps_alpha = self.soup.new_tag("li")
                            if ol_tag_for_roman.li:
                                li_tag_for_caps_alpha[
                                    'id'] = f"{ol_tag_for_roman.find_all('li', class_='roman')[-1].attrs['id']}-{caps_alpha_id}"
                                tag.attrs[
                                    'id'] = f"{ol_tag_for_roman.find_all('li', class_='roman')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}"
                            else:
                                li_tag_for_caps_alpha[
                                    'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}"
                                tag.attrs[
                                    'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{caps_roman}"
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
                    elif re.search(fr'^\({caps_alpha}{caps_alpha}?\) \({inner_num}\)', tag.text.strip()):
                        tag.name = "li"
                        caps_alpha_id = re.search(fr'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                  tag.text.strip()).group('caps_alpha_id')
                        tag.string = re.sub(fr'^\({caps_alpha}{caps_alpha}?\) \({inner_num}\)', '', tag.text.strip())
                        tag.wrap(ol_tag_for_inner_number)
                        li_tag_for_caps_alpha = self.soup.new_tag("li")
                        if ol_tag_for_roman.li:
                            li_tag_for_caps_alpha[
                                'id'] = f"{ol_tag_for_roman.find_all('li', class_='roman')[-1].attrs['id']}-{caps_alpha_id}"
                            tag.attrs[
                                'id'] = f"{ol_tag_for_roman.find_all('li', class_='roman')[-1].attrs['id']}-{caps_alpha_id}{inner_num}"
                        else:
                            li_tag_for_caps_alpha[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}"
                            tag.attrs[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}{inner_num}"
                        li_tag_for_caps_alpha['class'] = "caps_alpha"
                        tag['class'] = "inner_num"
                        li_tag_for_caps_alpha.append(ol_tag_for_inner_number)
                        ol_tag_for_caps_alphabet.append(li_tag_for_caps_alpha)
                        inner_num += 1
                        if caps_alpha == 'Z':
                            caps_alpha = 'A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                        if re.search(fr'^\({roman_number}\)', next_tag.text.strip()):
                            ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                ol_tag_for_inner_number)
                            ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                            ol_tag_for_inner_number = self.soup.new_tag("ol")
                            inner_num = 1
                            ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                            caps_alpha = 'A'
                    elif re.search(fr'^\({caps_alpha}{caps_alpha}?\) \({inner_roman}\)', tag.text.strip()):
                        tag.name = "li"
                        caps_alpha_id = re.search(fr'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                  tag.text.strip()).group('caps_alpha_id')
                        tag.string = re.sub(fr'^\({caps_alpha}{caps_alpha}?\) \({inner_roman}\)', '', tag.text.strip())
                        tag.wrap(ol_tag_for_inner_roman)
                        li_tag_for_caps_alpha = self.soup.new_tag("li")
                        if ol_tag_for_number.li:
                            li_tag_for_caps_alpha[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}"
                            tag.attrs[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{inner_roman}"
                        else:
                            li_tag_for_caps_alpha[
                                'id'] = f"{tag.find_previous({'h5', 'h4', 'h3'}).get('id')}ol{ol_count}-{caps_alpha_id}"
                            tag[
                                'id'] = f"{tag.find_previous({'h5', 'h4', 'h3'}).get('id')}ol{ol_count}-{caps_alpha_id}-{inner_roman}"
                        li_tag_for_caps_alpha['class'] = "caps_alpha"
                        tag['class'] = "inner_roman"
                        li_tag_for_caps_alpha.append(ol_tag_for_inner_roman)
                        ol_tag_for_caps_alphabet.append(li_tag_for_caps_alpha)
                        inner_roman = roman.fromRoman(inner_roman.upper())
                        inner_roman += 1
                        inner_roman = roman.toRoman(inner_roman).lower()
                        if caps_alpha == 'Z':
                            caps_alpha = 'A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                    elif re.search(fr'^\({caps_alpha}{caps_alpha}?\) \({roman_number}\)', tag.text.strip()):
                        tag.name = "li"
                        caps_alpha_id = re.search(fr'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                  tag.text.strip()).group('caps_alpha_id')
                        tag.string = re.sub(fr'^\({caps_alpha}{caps_alpha}?\) \({roman_number}\)', '', tag.text.strip())
                        tag.wrap(ol_tag_for_roman)
                        li_tag_for_caps_alpha = self.soup.new_tag("li")
                        if ol_tag_for_number.li:
                            li_tag_for_caps_alpha[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}"
                            tag.attrs[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}-{caps_alpha_id}-{roman_number}"
                        li_tag_for_caps_alpha['class'] = "caps_alpha"
                        tag['class'] = "roman"
                        li_tag_for_caps_alpha.append(ol_tag_for_roman)
                        ol_tag_for_caps_alphabet.append(li_tag_for_caps_alpha)
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                        if caps_alpha == 'Z':
                            caps_alpha = 'A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                    else:
                        if caps_alpha == "I" and re.search(r'^\(II\)', next_tag.text.strip()):
                            if re.search(fr'^\({caps_roman}\)', tag.text.strip()):
                                tag.name = "li"
                                tag.string = re.sub(fr'^\({caps_roman}\)', '', tag.text.strip())
                                if ol_tag_for_caps_roman.li:
                                    ol_tag_for_caps_roman.append(tag)
                                else:
                                    tag.wrap(ol_tag_for_caps_roman)
                                if ol_tag_for_inner_roman.li:
                                    id_of_last_li = \
                                        ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].attrs['id']
                                elif ol_tag_for_caps_alphabet.li:
                                    id_of_last_li = \
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                                elif ol_tag_for_roman.li:
                                    id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                                elif ol_tag_for_number.li:
                                    id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                                tag['id'] = f"{id_of_last_li}-{caps_roman}"
                                tag['class'] = "caps_roman"
                                caps_roman = roman.fromRoman(caps_roman)
                                caps_roman += 1
                                caps_roman = roman.toRoman(caps_roman)
                                while (re.search("^[a-z A-Z]+",
                                                 next_tag.text.strip()) or next_tag.next_element.name == "br") and next_tag.name != "h4" and next_tag.name != "h3":
                                    if next_tag.next_element.name == "br":
                                        next_tag = self.decompose_break_tag(next_tag)
                                    else:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                count_of_p_tag = 1
                                if re.search(fr'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()) and re.search(
                                        fr'^\((?P<caps_id>{caps_alpha}{caps_alpha}?)\)', next_tag.text.strip()).group('caps_id') != "II":
                                    if ol_tag_for_inner_roman.li:
                                        ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].append(
                                            ol_tag_for_caps_roman)
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_inner_roman)
                                        ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                        inner_roman = "i"
                                    else:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_caps_roman)
                                    ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                    caps_roman = 'I'
                                elif re.search(fr'^\({roman_number}\)', next_tag.text.strip()) and roman_number != "i":
                                    if ol_tag_for_caps_alphabet.li:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_caps_roman)
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_caps_alphabet)
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = 'A'
                                    else:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_caps_roman)
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'
                                elif re.search(fr'^\({number}\)', next_tag.text.strip()):
                                    if ol_tag_for_caps_alphabet.li:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_caps_roman)
                                        if ol_tag_for_roman.li:
                                            ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                                ol_tag_for_caps_alphabet)
                                            ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                                ol_tag_for_roman)
                                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                            roman_number = "i"
                                        else:
                                            ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                                ol_tag_for_caps_alphabet)
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = 'A'
                                    elif ol_tag_for_roman.li:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_caps_roman)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'

                                elif re.search(fr'^\({inner_alphabet}\)',
                                               next_tag.text.strip()) and inner_alphabet != "a":
                                    if ol_tag_for_roman.li:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_caps_roman)
                                        ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'
                                elif next_tag.name == "h4":
                                    if ol_tag_for_caps_alphabet.li:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_caps_roman)
                                        if ol_tag_for_roman.li:
                                            ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                                ol_tag_for_caps_alphabet)
                                            ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                                ol_tag_for_roman)
                                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                            roman_number = "i"
                                        else:
                                            ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                                ol_tag_for_caps_alphabet)
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = 'A'
                                        ol_tag_for_number = self.soup.new_tag("ol")
                                        number = 1
                                    elif ol_tag_for_roman.li:
                                        ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                            ol_tag_for_caps_roman)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'
                            else:
                                tag.name = "li"
                                tag.string = re.sub(fr'^\({inner_caps_roman}\)', '', tag.text.strip())
                                if ol_tag_for_inner_caps_roman.li:
                                    ol_tag_for_inner_caps_roman.append(tag)
                                else:
                                    tag.wrap(ol_tag_for_inner_caps_roman)
                                if ol_tag_for_roman.li:
                                    id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']

                                tag['id'] = f"{id_of_last_li}-{inner_caps_roman}"
                                tag['class'] = "inner_caps_roman"
                                inner_caps_roman = roman.fromRoman(inner_caps_roman)
                                inner_caps_roman += 1
                                inner_caps_roman = roman.toRoman(inner_caps_roman)
                                while re.search("^[a-z A-Z]+",
                                                next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                count_of_p_tag = 1
                                if re.search(fr'^\({number}\)', next_tag.text.strip()):
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                        ol_tag_for_inner_caps_roman)
                                    if ol_tag_for_caps_roman.li:
                                        ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_caps_roman)
                                        ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                        roman_number = "i"
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = 'I'
                                    else:
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_inner_caps_roman = self.soup.new_tag("ol", type="I")
                                    inner_caps_roman = 'I'
                        else:
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            caps_alpha_id = re.search(fr'^\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                      tag.text.strip()).group('caps_alpha_id')
                            tag.string = re.sub(fr'^\({caps_alpha}{caps_alpha}?\)', '', tag.text.strip())
                            tag['class'] = "caps_alpha"
                            tag.wrap(ol_tag_for_caps_alphabet)
                            if ol_tag_for_roman.li:
                                id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                            elif ol_tag_for_number.li:
                                id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                            else:
                                id_of_last_li = h3_id
                            tag['id'] = f"{id_of_last_li}-{caps_alpha_id}"
                            if caps_alpha == "Z":
                                caps_alpha = 'A'
                            else:
                                caps_alpha = chr(ord(caps_alpha) + 1)
                            while (re.search(r"^“?[a-z A-Z]+|^\((ix|iv|v?i{0,3})\)|^\([A-Z]+\)",
                                             next_tag.text.strip()) or next_tag.next_element.name == "br") and next_tag.name != "h4" and next_tag.name != "h3":
                                if next_tag.next_element.name == "br":
                                    next_tag = self.decompose_break_tag(next_tag)
                                elif re.search(r'^\((ix|iv|v?i{0,3})\)', next_tag.text.strip()):
                                    roman_id = re.search(r'^\((?P<roman_id>(ix|iv|v?i{0,3}))\)',
                                                         next_tag.text.strip()).group('roman_id')
                                    if roman_id != roman_number and roman_id != inner_roman:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                                elif re.search(r'^\([A-Z]+\)', next_tag.text.strip()):
                                    caps_id = re.search(r'^\((?P<caps_id>[A-Z]+)\)', next_tag.text.strip()).group(
                                        'caps_id')
                                    if caps_id[0] != caps_alpha and caps_id[0] != caps_roman and caps_id[0] != inner_caps_roman:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                                else:
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                            count_of_p_tag = 1
                            if re.search(fr'^\({inner_roman}\)', next_tag.text.strip()) and ol_tag_for_caps_alphabet.li:
                                continue
                            elif re.search(fr'^\({roman_number}\)', next_tag.text.strip()):
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = 'A'
                            elif re.search(fr'^\({number}\)|^{number}\.', next_tag.text.strip()) and number != 1:
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    if ol_tag_for_inner_alphabet.li:
                                        ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_inner_alphabet)
                                        ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                        inner_alphabet = "a"
                                    elif ol_tag_for_number.li:
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
                            elif re.search(fr'^\({inner_alphabet}\)', next_tag.text.strip()) and ol_tag_for_number.li:
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                        ol_tag_for_roman)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = 'A'
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = 'i'
                            elif re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()):
                                if ol_tag_for_roman.li:
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
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_caps_alphabet)
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = 'A'
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                else:
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                        ol_tag_for_caps_alphabet)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = 'A'
                            elif next_tag.name == "h4" or next_tag.name == "h3":
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    if ol_tag_for_number.li:
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                        if ol_tag_for_alphabet.li:
                                            ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                                ol_tag_for_number)
                                            ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                            alphabet = 'a'
                                        ol_tag_for_number = self.soup.new_tag("ol")
                                        number = 1
                                    else:
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_roman)
                                        ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                        alphabet = 'a'
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = 'A'
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_caps_alphabet)
                                    if ol_tag_for_alphabet.li:
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_number)
                                        ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                        alphabet = 'a'
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = 'A'
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                else:
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = 'A'
                elif re.search(fr'^\({caps_roman}\)|^\({inner_caps_roman}\)', tag.text.strip()):
                    if re.search(fr'^\({caps_roman}\)', tag.text.strip()):
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({caps_roman}\)', '', tag.text.strip())
                        if ol_tag_for_caps_roman.li:
                            ol_tag_for_caps_roman.append(tag)
                        else:
                            tag.wrap(ol_tag_for_caps_roman)
                        if ol_tag_for_inner_roman.li:
                            id_of_last_li = ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].attrs['id']
                        elif ol_tag_for_caps_alphabet.li:
                            id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                        elif ol_tag_for_roman.li:
                            id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                        elif ol_tag_for_number.li:
                            id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                        tag['id'] = f"{id_of_last_li}-{caps_roman}"
                        tag['class'] = "caps_roman"
                        caps_roman = roman.fromRoman(caps_roman)
                        caps_roman += 1
                        caps_roman = roman.toRoman(caps_roman)
                        while (re.search("^[a-z A-Z]+",
                                         next_tag.text.strip()) or next_tag.next_element.name == "br") and next_tag.name != "h4" and next_tag.name != "h3":
                            if next_tag.next_element.name == "br":
                                next_tag = self.decompose_break_tag(next_tag)
                            else:
                                next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                        count_of_p_tag = 1
                        if re.search(fr'^\({caps_alpha}{caps_alpha}?\)',
                                     next_tag.text.strip()) and f'{caps_alpha}{caps_alpha}?' != "II":
                            if ol_tag_for_inner_roman.li:
                                ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].append(
                                    ol_tag_for_caps_roman)
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_inner_roman)
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = "i"
                            else:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_caps_roman)
                            ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                            caps_roman = 'I'
                        elif re.search(fr'^\({roman_number}\)', next_tag.text.strip()) and roman_number != "i":
                            if ol_tag_for_caps_alphabet.li:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_caps_roman)
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                            else:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_roman)
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'
                        elif re.search(fr'^\({number}\)', next_tag.text.strip()):
                            if ol_tag_for_caps_alphabet.li:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_caps_roman)
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                else:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_caps_alphabet)
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                            elif ol_tag_for_roman.li:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_roman)
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = "i"
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'

                        elif re.search(fr'^\({inner_alphabet}\)', next_tag.text.strip()) and inner_alphabet != "a":
                            if ol_tag_for_roman.li:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_roman)
                                ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                    ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = "i"
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'
                        elif next_tag.name == "h4":
                            if ol_tag_for_caps_alphabet.li:
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_caps_roman)
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                else:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_caps_alphabet)
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'
                                ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                caps_alpha = 'A'
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                            elif ol_tag_for_roman.li:
                                ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_roman)
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = "i"
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'
                    else:
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({inner_caps_roman}\)', '', tag.text.strip())
                        if ol_tag_for_inner_caps_roman.li:
                            ol_tag_for_inner_caps_roman.append(tag)
                        else:
                            tag.wrap(ol_tag_for_inner_caps_roman)
                        if ol_tag_for_roman.li:
                            id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']

                        tag['id'] = f"{id_of_last_li}-{inner_caps_roman}"
                        tag['class'] = "inner_caps_roman"
                        inner_caps_roman = roman.fromRoman(inner_caps_roman)
                        inner_caps_roman += 1
                        inner_caps_roman = roman.toRoman(inner_caps_roman)
                        while re.search("^[a-z A-Z]+",
                                        next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                            next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                        count_of_p_tag = 1
                        if re.search(fr'^\({number}\)', next_tag.text.strip()):
                            ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                ol_tag_for_inner_caps_roman)
                            if ol_tag_for_caps_roman.li:
                                ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].append(ol_tag_for_roman)
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_caps_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = "i"
                                ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                caps_roman = 'I'
                            else:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                            ol_tag_for_inner_caps_roman = self.soup.new_tag("ol", type="I")
                            inner_caps_roman = 'I'
                elif re.search(fr'^\({roman_number}\)|^\({inner_roman}\)', tag.text.strip()) and (
                        ol_tag_for_number.li or alphabet != roman_number) and inner_roman != inner_alphabet:
                    if re.search(fr'^\({roman_number}\) \({caps_alpha}{caps_alpha}?\)', tag.text.strip()):
                        caps_alpha_id = re.search(fr'\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                  tag.text.strip()).group('caps_alpha_id')
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({roman_number}\) \({caps_alpha}{caps_alpha}?\)', '', tag.text.strip())
                        tag['class'] = "caps_alpha"
                        tag.wrap(ol_tag_for_caps_alphabet)
                        li_tag = self.soup.new_tag("li")
                        if ol_tag_for_number.li:
                            id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                        elif ol_tag_for_alphabet.li:
                            id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs['id']
                        li_tag['id'] = f"{id_of_last_li}-{roman_number}"
                        li_tag['class'] = "roman"
                        li_tag.append(ol_tag_for_caps_alphabet)
                        tag.attrs['id'] = f"{id_of_last_li}-{roman_number}-{caps_alpha_id}"
                        if caps_alpha == 'Z':
                            caps_alpha = 'A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                        ol_tag_for_roman.append(li_tag)
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                    elif re.search(fr'^\({inner_roman}\)', tag.text.strip()) and inner_roman != inner_alphabet and (
                            ol_tag_for_caps_alphabet.li or ol_tag_for_inner_number.li):
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({inner_roman}\)', '', tag.text.strip())
                        tag.wrap(ol_tag_for_inner_roman)
                        tag['class'] = "inner_roman"
                        if ol_tag_for_inner_alphabet.li:
                            id_of_last_li = ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs[
                                'id']
                        elif ol_tag_for_inner_number.li:
                            id_of_last_li = ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].attrs['id']
                        elif ol_tag_for_caps_roman.li:
                            id_of_last_li = ol_tag_for_caps_roman.find_all("li")[-1].attrs['id']
                        elif ol_tag_for_caps_alphabet.li:
                            id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                        elif ol_tag_for_roman.li:
                            id_of_last_li = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                        tag['id'] = f"{id_of_last_li}-{inner_roman}"
                        inner_roman = roman.fromRoman(inner_roman.upper())
                        inner_roman += 1
                        inner_roman = roman.toRoman(inner_roman).lower()
                        while re.search("^[a-z A-Z]+",
                                        next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                            next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                        count_of_p_tag = 1
                        if re.search(fr'^\({inner_num}\)', next_tag.text.strip()) and inner_num != 1:
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                    ol_tag_for_inner_roman)
                                if ol_tag_for_inner_number.li:
                                    ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = "a"
                            elif ol_tag_for_inner_number.li:
                                ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                    ol_tag_for_inner_roman)
                            ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                            inner_roman = 'i'
                        elif re.search(fr'^\({number}\)', next_tag.text.strip()) and number != 1:
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
                                elif ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_number)
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
                        elif re.search(fr'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()):
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                    ol_tag_for_inner_roman)
                                if ol_tag_for_inner_number.li:
                                    ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    if ol_tag_for_caps_alphabet.li:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_inner_number)
                                        ol_tag_for_inner_number = self.soup.new_tag("ol")
                                        inner_num = 1
                                    ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                    inner_alphabet = 'a'
                                ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                inner_roman = 'i'
                            elif ol_tag_for_inner_number.li:
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
                        elif re.search(fr'^\({alphabet}{alphabet}?\)',
                                       next_tag.text.strip()) and alphabet != 'a' and inner_roman != "ii" and roman_number != "ii":
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
                        elif re.search(fr'\({caps_roman}\)', next_tag.text.strip()) and caps_roman != "I":

                            ol_tag_for_caps_roman.find_all("li")[-1].append(ol_tag_for_inner_roman)
                            ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                            inner_roman = "i"
                    else:
                        h3_id = tag.find_previous_sibling("h3").attrs['id']
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({roman_number}\)', '', tag.text.strip())
                        if ol_tag_for_roman.li:
                            ol_tag_for_roman.append(tag)
                        else:
                            tag.wrap(ol_tag_for_roman)
                        tag['class'] = "roman"
                        if ol_tag_for_inner_alphabet.li:
                            id_of_last_li = ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs[
                                'id']
                        elif ol_tag_for_caps_roman.li:
                            id_of_last_li = ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].attrs['id']
                        elif ol_tag_for_number.li:
                            id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                        elif ol_tag_for_alphabet.li:
                            id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs['id']
                        else:
                            id_of_last_li = h3_id
                        tag['id'] = f"{id_of_last_li}-{roman_number}"
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                        while next_tag.name != "h4" and next_tag.name != "h3" and (re.search(
                                r'^“?[a-z A-Z]+|^\[See .*]|^\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\)|^\([A-Z]+\)|^\([0-9]+\)|^\([a-z]+\)',
                                next_tag.text.strip()) or (
                                                                                           next_tag.next_element and next_tag.next_element.name == "br")):
                            if next_tag.next_element.name == "br":
                                next_tag = self.decompose_break_tag(next_tag)
                            elif re.search(
                                    r"^“?[a-z A-Z]+|^\[See .*]|^\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\)|^\([A-Z]+\)|^\([a-z]+\)|^\([0-9]+\)",
                                    next_tag.text.strip()):
                                if re.search(r"^“?[a-z A-Z]+|^\[See .*]", next_tag.text.strip()):
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                elif re.search(r'^\((xc|xl|l?x{0,3})(ix|iv|v?i{0,3})\)', next_tag.text.strip()):
                                    roman_id = re.search(r'^\((?P<roman_id>(xc|xl|l?x{0,3})(ix|iv|v?i{0,3}))\)',
                                                         next_tag.text.strip()).group('roman_id')
                                    if roman_id != roman_number and roman_id != alphabet:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                                elif re.search(r"^\([A-Z]+\)", next_tag.text.strip()):
                                    alpha_id = re.search(r"^\((?P<alpha_id>[A-Z]+)\)", next_tag.text.strip()).group(
                                        'alpha_id')
                                    if alpha_id[0] != caps_alpha and alpha_id[0] != caps_roman and alpha_id[0] != inner_caps_roman:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                                elif re.search(r"^\([a-z]+\)", next_tag.text.strip()):
                                    alpha_id = re.search(r"^\((?P<alpha_id>[a-z]+)\)", next_tag.text.strip()).group(
                                        'alpha_id')
                                    if alpha_id[0] != alphabet and alpha_id[0] != inner_alphabet:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                                elif re.search(r"^\([0-9]+\)", next_tag.text.strip()):
                                    number_id = re.search(r"^\((?P<number_id>[0-9]+)\)", next_tag.text.strip()).group(
                                        'number_id')
                                    if number_id != str(number) and number_id != str(inner_num):
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                        count_of_p_tag = 1
                        if re.search(fr'^\({number}\)', next_tag.text.strip()) and number != 1:
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
                                ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                    ol_tag_for_roman)
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = "a"
                            elif ol_tag_for_number.li:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                        elif re.search(fr'^\({caps_alpha}{caps_alpha}?\)',
                                       next_tag.text.strip()) and ol_tag_for_caps_alphabet.li:
                            ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(ol_tag_for_roman)
                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                            roman_number = "i"
                        elif re.search(fr'^\({roman_number}\)', next_tag.text.strip()) and ol_tag_for_number.li:
                            continue
                        elif re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()) and alphabet != "a":
                            if ol_tag_for_number.li:
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                    ol_tag_for_number)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                            elif ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                    ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = 'i'
                        elif re.search(fr'^\({inner_alphabet}\)', next_tag.text.strip()) and inner_alphabet != 'a':
                            ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(ol_tag_for_roman)
                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                            roman_number = "i"
                        elif next_tag.name == "h4" or next_tag.name == "h3":
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                    ol_tag_for_roman)
                                if ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                    inner_alphabet = "a"
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
                elif re.search(fr'^\({alphabet}{alphabet}?\)|^\({inner_alphabet}\)', tag.text.strip().strip('\"')) and (
                        inner_roman != "ii" and roman_number != "ii"):
                    if re.search(fr'^\({alphabet}{alphabet}?\) \({number}\)', tag.text.strip()):
                        if re.search(fr'^\({alphabet}{alphabet}?\) \({number}\) \({roman_number}\)', tag.text.strip()):
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({alphabet}{alphabet}?\) \({number}\) \({roman_number}\)', '',
                                                tag.text.strip())
                            tag.wrap(ol_tag_for_roman)
                            li_tag_for_alphabet = self.soup.new_tag("li")
                            li_tag_for_alphabet['id'] = f"{h3_id}ol{ol_count}{alphabet}"
                            li_tag_for_alphabet['class'] = "alphabet"
                            li_tag_for_number = self.soup.new_tag("li")
                            li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}"
                            li_tag_for_number['class'] = "number"
                            li_tag_for_number.append(ol_tag_for_roman)
                            ol_tag_for_number.append(li_tag_for_number)
                            li_tag_for_alphabet.append(ol_tag_for_number)
                            ol_tag_for_alphabet.append(li_tag_for_alphabet)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}-{roman_number}"
                            tag['class'] = "roman"
                            number += 1
                            alphabet = chr(ord(alphabet) + 1)
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            while re.search("^[a-z A-Z]+",
                                            next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                                next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                            count_of_p_tag = 1
                        elif re.search(fr'^\({alphabet}{alphabet}?\) \({number}\) \({inner_alphabet}\)',
                                       tag.text.strip()):
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({alphabet}{alphabet}?\) \({number}\) \({inner_alphabet}\)', '',
                                                tag.text.strip())
                            tag.wrap(ol_tag_for_inner_alphabet)
                            li_tag_for_alphabet = self.soup.new_tag("li")
                            li_tag_for_alphabet['id'] = f"{h3_id}ol{ol_count}{alphabet}"
                            li_tag_for_alphabet['class'] = "alphabet"
                            li_tag_for_number = self.soup.new_tag("li")
                            li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}"
                            li_tag_for_number['class'] = "number"
                            li_tag_for_number.append(ol_tag_for_inner_alphabet)
                            ol_tag_for_number.append(li_tag_for_number)
                            li_tag_for_alphabet.append(ol_tag_for_number)
                            ol_tag_for_alphabet.append(li_tag_for_alphabet)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}-{inner_alphabet}"
                            tag['class'] = "inner_alpha"
                            number += 1
                            alphabet = chr(ord(alphabet) + 1)
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                            while re.search("^[a-z A-Z]+",
                                            next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                                next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                            count_of_p_tag = 1
                        elif re.search(fr'^\({alphabet}{alphabet}?\) \({number}\) \({caps_alpha}{caps_alpha}?\)',
                                       tag.text.strip()):
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            tag.string = re.sub(
                                fr'^\({alphabet}{alphabet}?\) \({number}\) \({caps_alpha}{caps_alpha}?\)', '',
                                tag.text.strip())
                            tag.wrap(ol_tag_for_caps_alphabet)
                            li_tag_for_alphabet = self.soup.new_tag("li")
                            li_tag_for_alphabet['id'] = f"{h3_id}ol{ol_count}{alphabet}"
                            li_tag_for_alphabet['class'] = "alphabet"
                            li_tag_for_number = self.soup.new_tag("li")
                            li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}"
                            li_tag_for_number['class'] = "number"
                            li_tag_for_number.append(ol_tag_for_caps_alphabet)
                            ol_tag_for_number.append(li_tag_for_number)
                            li_tag_for_alphabet.append(ol_tag_for_number)
                            ol_tag_for_alphabet.append(li_tag_for_alphabet)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{alphabet}{number}-{caps_alpha}"
                            tag['class'] = "caps_alpha"
                            number += 1
                            alphabet = chr(ord(alphabet) + 1)
                            caps_alpha = chr(ord(caps_alpha) + 1)
                            while re.search("^[a-z A-Z]+",
                                            next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                                next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                            count_of_p_tag = 1
                        else:
                            alpha_id = re.search(fr'^\((?P<alpha_id>{alphabet}{alphabet}?)\)', tag.text.strip()).group(
                                'alpha_id')
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({alphabet}{alphabet}?\) \({number}\)', '', tag.text.strip())
                            tag.wrap(ol_tag_for_number)
                            li_tag = self.soup.new_tag("li")
                            li_tag['id'] = f"{h3_id}ol{ol_count}{alpha_id}"
                            li_tag['class'] = "alphabet"
                            ol_tag_for_number.wrap(li_tag)
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{alpha_id}{number}"
                            tag['class'] = "number"
                            li_tag.wrap(ol_tag_for_alphabet)
                            number += 1
                            alphabet = chr(ord(alphabet) + 1)
                            while (re.search("^[a-z A-Z]+",
                                             next_tag.text.strip()) or next_tag.next_element.name == "br") and next_tag.name != "h4" and next_tag.name != "h3":
                                if next_tag.next_element.name == "br":
                                    next_tag = self.decompose_break_tag(next_tag)
                                else:
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                            count_of_p_tag = 1
                            if re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()) and not re.search(
                                    r'^\(ii\)', next_tag.find_next_sibling().text.strip()):
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                    elif re.search(fr'^\({alphabet}{alphabet}?\) \({roman_number}\)',
                                   tag.text.strip()) and not ol_tag_for_number.li:
                        h3_id = tag.find_previous_sibling("h3").attrs['id']
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({alphabet}{alphabet}?\) \({roman_number}\)', '', tag.text.strip())
                        tag.wrap(ol_tag_for_roman)
                        li_tag = self.soup.new_tag("li")
                        li_tag['id'] = f"{h3_id}ol{ol_count}{alphabet}"
                        li_tag['class'] = "alphabet"
                        ol_tag_for_roman.wrap(li_tag)
                        tag.attrs['id'] = f"{h3_id}ol{ol_count}{alphabet}-{roman_number}"
                        tag['class'] = "roman"
                        if ol_tag_for_alphabet.li:
                            ol_tag_for_alphabet.append(li_tag)
                        else:
                            li_tag.wrap(ol_tag_for_alphabet)
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                        alphabet = chr(ord(alphabet) + 1)
                    elif re.search(fr'^\({alphabet}{alphabet}?\)', tag.text.strip()) and (
                            not ol_tag_for_number.li and not ol_tag_for_caps_alphabet.li and not ol_tag_for_inner_number.li):
                        alpha_id = re.search(fr'^\((?P<alpha_id>{alphabet}{alphabet}?)\)', tag.text.strip()).group(
                            'alpha_id')
                        if alphabet == "i" and re.search(fr'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()):
                            sibling_of_i = tag.find_next_sibling(
                                lambda sibling_tag: re.search(r'^\(ii\)|^History of Section\.',
                                                              sibling_tag.text.strip()))
                            if re.search(r'^\(ii\)', sibling_of_i.text.strip()):
                                if re.search(fr'^\({roman_number}\) \({caps_alpha}{caps_alpha}?\)', tag.text.strip()):
                                    caps_alpha_id = re.search(fr'\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                              tag.text.strip()).group('caps_alpha_id')
                                    tag.name = "li"
                                    tag.string = re.sub(fr'^\({roman_number}\) \({caps_alpha}{caps_alpha}?\)', '',
                                                        tag.text.strip())
                                    tag['class'] = "caps_alpha"
                                    tag.wrap(ol_tag_for_caps_alphabet)
                                    li_tag = self.soup.new_tag("li")
                                    if ol_tag_for_number.li:
                                        id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs[
                                            'id']
                                    elif ol_tag_for_alphabet.li:
                                        id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs[
                                            'id']
                                    li_tag['id'] = f"{id_of_last_li}-{roman_number}"
                                    li_tag['class'] = "roman"
                                    li_tag.append(ol_tag_for_caps_alphabet)
                                    tag.attrs['id'] = f"{id_of_last_li}-{roman_number}-{caps_alpha_id}"
                                    if caps_alpha == 'Z':
                                        caps_alpha = 'A'
                                    else:
                                        caps_alpha = chr(ord(caps_alpha) + 1)
                                    ol_tag_for_roman.append(li_tag)
                                    roman_number = roman.fromRoman(roman_number.upper())
                                    roman_number += 1
                                    roman_number = roman.toRoman(roman_number).lower()
                                else:
                                    tag.name = "li"
                                    tag.string = re.sub(fr'^\({roman_number}\)', '', tag.text.strip())

                                    tag.wrap(ol_tag_for_roman)
                                    tag['class'] = "roman"
                                    if ol_tag_for_number.li:
                                        id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs[
                                            'id']
                                    elif ol_tag_for_alphabet.li:
                                        id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs[
                                            'id']
                                    tag['id'] = f"{id_of_last_li}-{roman_number}"
                                    roman_number = roman.fromRoman(roman_number.upper())
                                    roman_number += 1
                                    roman_number = roman.toRoman(roman_number).lower()
                                    while (re.search('^“?[a-z A-Z]+', next_tag.text.strip()) or (
                                            next_tag.next_element and next_tag.next_element.name == "br")) and next_tag.name != "h4" and next_tag.name != "h3":
                                        if next_tag.next_element.name == "br":
                                            next_tag = self.decompose_break_tag(next_tag)
                                        elif re.search("^“?[a-z A-Z]+",
                                                       next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                                            next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag,
                                                                                            count_of_p_tag)
                                    count_of_p_tag = 1
                                    if re.search(fr'^\({number}\)', next_tag.text.strip()):
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
                                    elif re.search(fr'^\({roman_number}\)', next_tag.text.strip()):
                                        continue
                                    elif re.search(fr'^\({alphabet}{alphabet}?\)',
                                                   next_tag.text.strip()) and alphabet != "a":
                                        if ol_tag_for_number.li:
                                            ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                                ol_tag_for_roman)
                                            ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                                ol_tag_for_number)
                                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                            roman_number = 'i'
                                            ol_tag_for_number = self.soup.new_tag("ol")
                                            number = 1
                                        elif ol_tag_for_alphabet.li:
                                            ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                                ol_tag_for_roman)
                                            ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                            roman_number = 'i'
                            else:
                                tag.name = "li"
                                tag.string = re.sub(fr'^\({alphabet}{alphabet}?\)', '', tag.text.strip())
                                tag[
                                    'id'] = f"{tag.find_previous(['h4', 'h3'], ['schedule', 'comment', 'section', 'article_h3']).get('id')}ol{ol_count}{alpha_id}"
                                tag.wrap(ol_tag_for_alphabet)
                                if alphabet == "z":
                                    alphabet = 'a'
                                else:
                                    alphabet = chr(ord(alphabet) + 1)
                                tag['class'] = "alphabet"
                                while (next_tag.name != "h4" and next_tag.name != "h3" and not re.search(
                                        r'^ARTICLE [IVXCL]+|^Section \d+|^[IVXCL]+. Purposes\.', next_tag.text.strip(),
                                        re.IGNORECASE)) and (
                                        re.search(
                                            r'^“?(\*\*)?[a-z A-Z]+|^\(Address\)|^\(Landowner.*\)|^_______________|^\[See .*]|^\(Name .*\)|^\([0-9]+\)',
                                            next_tag.text.strip()) or (
                                                next_tag.next_element and next_tag.next_element.name == "br")):
                                    if next_tag.next_element.name == "br":
                                        next_tag = self.decompose_break_tag(next_tag)

                                    elif re.search(fr'^\([0-9]+\)', next_tag.text.strip()):
                                        number_id = re.search(fr'^\((?P<number_id>[0-9]+)\)',
                                                              next_tag.text.strip()).group('number_id')
                                        if number_id != str(number) and number != str(inner_num):
                                            next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag,
                                                                                            count_of_p_tag)
                                        else:
                                            break
                                    else:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                count_of_p_tag = 1
                                if re.search('^ARTICLE [IVXCL]+', next_tag.text.strip(),
                                             re.IGNORECASE):
                                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                    alphabet = 'a'
                                    ol_count = 1
                                    continue
                                elif re.search(r'^[IVXCL]+. Purposes\.', next_tag.text.strip()):
                                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                    alphabet = 'a'
                                    ol_count += 1

                                elif re.search(r'^Section \d+', next_tag.text.strip()):
                                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                    alphabet = 'a'
                                    if re.search(r'\(a\)|\(\d\)', next_tag.find_next_sibling().text.strip()):
                                        ol_count += 1
                                elif next_tag.name == "h4" or next_tag.name == "h3":
                                    ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                    alphabet = 'a'
                        else:
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({alphabet}{alphabet}?\)', '', tag.text.strip())
                            tag.attrs[
                                'id'] = f"{tag.find_previous(['h4', 'h3'], ['schedule', 'comment', 'section', 'article_h3']).get('id')}ol{ol_count}{alpha_id}"
                            tag.wrap(ol_tag_for_alphabet)
                            if alphabet == "z":
                                alphabet = 'a'
                            else:
                                alphabet = chr(ord(alphabet) + 1)
                            tag['class'] = "alphabet"
                            while (next_tag.name != "h4" and next_tag.name != "h3" and not re.search(
                                    r'^ARTICLE [IVXCL]+^ARTICLE [IVXCL]+|^Section \d+|^[IVXCL]+. Purposes\.|^Part [IVXCL]+',
                                    next_tag.text.strip(), re.IGNORECASE)) and (re.search(
                                    r'^“?(\*\*)?[a-z A-Z]+|^\(Address\)|^\(Landowner.*\)|^_______________|^\[See .*]|^\(Name .*\)|^\([0-9]+\)',
                                    next_tag.text.strip()) or (
                                                                                        next_tag.next_element and next_tag.next_element.name == "br")):
                                if next_tag.next_element.name == "br":
                                    next_tag = self.decompose_break_tag(next_tag)
                                elif re.search(fr'^\([0-9]+\)', next_tag.text.strip()):
                                    number_id = re.search(fr'^\((?P<number_id>[0-9]+)\)', next_tag.text.strip()).group(
                                        'number_id')
                                    if number_id != str(number) and number != str(inner_num):
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                                else:
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                            count_of_p_tag = 1
                            if re.search('^ARTICLE [IVXCL]+|^Part [IVXCL]+', next_tag.text.strip(),
                                         re.IGNORECASE):
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                                ol_count = 1
                                if re.search('^Part [IVXCL]+', next_tag.text.strip()):
                                    next_tag['class'] = "h3_part"
                            elif re.search(r'^[IVXCL]+. Purposes\.', next_tag.text.strip()):
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                                ol_count += 1
                            elif re.search(r'^Section \d+', next_tag.text.strip()):
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                                if re.search(r'\(a\)|\(\d\)', next_tag.find_next_sibling().text.strip()):
                                    ol_count += 1
                            elif next_tag.name == "h4" or next_tag.name == "h3":
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                    else:
                        if re.search(fr'^\({inner_alphabet}\) \({roman_number}\)', tag.text.strip()):
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({inner_alphabet}\) \({roman_number}\)', '', tag.text.strip())
                            tag.wrap(ol_tag_for_roman)
                            li_tag = self.soup.new_tag("li")
                            li_tag[
                                'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}{inner_alphabet}"
                            li_tag['class'] = "inner_alpha"
                            ol_tag_for_roman.wrap(li_tag)
                            tag.attrs[
                                'id'] = f'{ol_tag_for_number.find_all("li", class_="number")[-1].attrs["id"]}{inner_alphabet}-{roman_number}'
                            tag['class'] = "roman"
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.append(li_tag)
                            else:
                                li_tag.wrap(ol_tag_for_inner_alphabet)
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                        else:
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({inner_alphabet}\)', '', tag.text.strip())
                            if ol_tag_for_inner_alphabet.li:
                                ol_tag_for_inner_alphabet.append(tag)
                            else:
                                tag.wrap(ol_tag_for_inner_alphabet)
                            id_of_alpha = None
                            if ol_tag_for_inner_roman.li:
                                id_of_alpha = ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].attrs[
                                    'id']
                            elif ol_tag_for_caps_roman.li:
                                id_of_alpha = ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].attrs['id']
                            elif ol_tag_for_inner_number.li:
                                id_of_alpha = ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].attrs['id']
                            elif ol_tag_for_roman.li:
                                id_of_alpha = ol_tag_for_roman.find_all("li", class_="roman")[-1].attrs['id']
                            elif ol_tag_for_number.li:
                                id_of_alpha = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                            tag.attrs['id'] = f"{id_of_alpha}{inner_alphabet}"
                            tag['class'] = "inner_alpha"
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                            while (re.search(r'^“?[a-z A-Z]+|^\([0-9]+\)', next_tag.text.strip()) or (
                                    next_tag.next_element and next_tag.next_element.name == "br")) and next_tag.name != "h4" and next_tag.name != "h3":
                                if next_tag.next_element.name == "br":
                                    next_tag = self.decompose_break_tag(next_tag)
                                elif re.search("^“?[a-z A-Z]+",
                                               next_tag.text.strip()) and next_tag.name != "h4" and next_tag.name != "h3":
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                elif re.search(r"^\([0-9]+\)", next_tag.text.strip()):
                                    number_id = re.search(r"^\((?P<number_id>[0-9]+)\)", next_tag.text.strip()).group(
                                        'number_id')
                                    if number_id != str(number) and number_id != str(inner_num):
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                            count_of_p_tag = 1
                            if re.search(fr'^\({inner_num}\)', next_tag.text.strip()) and inner_num != 1:
                                ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                    ol_tag_for_inner_alphabet)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = "a"
                            elif re.search(fr'^\({number}\)|^{number}\.', next_tag.text.strip()) and number != 1:
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                    inner_alphabet = 'a'
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                    inner_alphabet = 'a'
                            elif re.search(fr'^\({inner_roman}\)', next_tag.text.strip()) and inner_roman != "i":
                                ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].append(
                                    ol_tag_for_inner_alphabet)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = 'a'
                            elif re.search(fr'^\({caps_roman}\)', next_tag.text.strip()) and caps_roman != 'I':
                                ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].append(
                                    ol_tag_for_inner_alphabet)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = "a"
                            elif re.search(fr'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()):
                                ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                    ol_tag_for_inner_alphabet)
                                ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                    ol_tag_for_inner_number)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = "a"
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1
                            elif re.search(fr'^\({inner_alphabet}\)',
                                           next_tag.text.strip()) and inner_alphabet == alphabet:
                                sibling_of_alpha = next_tag.find_next_sibling(
                                    lambda sibling_tag: re.search(r'^\([1-9]\)|^\(ii\)', sibling_tag.text.strip()))
                                if ol_tag_for_alphabet.li and re.search(fr'^\(1\)', sibling_of_alpha.text.strip()):
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                    ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                    inner_alphabet = "a"
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                else:
                                    continue
                            elif re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()):
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = "a"
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                            elif next_tag.name == "h4" or next_tag.name == "h3":
                                if ol_tag_for_caps_roman.li:
                                    ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    if ol_tag_for_caps_alphabet.li:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_caps_roman)
                                        if ol_tag_for_number.li:
                                            ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                                ol_tag_for_caps_alphabet)
                                            if ol_tag_for_alphabet.li:
                                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                                    ol_tag_for_number)
                                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                                alphabet = "a"
                                                ol_tag_for_number = self.soup.new_tag("ol")
                                                number = 1
                                            ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                            caps_alpha = "A"
                                        ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                        caps_roman = "I"
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    if ol_tag_for_alphabet.li:
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_number)
                                        ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                        alphabet = "a"
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                elif ol_tag_for_inner_number.li:
                                    ol_tag_for_inner_number.find_all("li", class_="inner_num")[-1].append(
                                        ol_tag_for_inner_alphabet)
                                    if ol_tag_for_caps_alphabet.li:
                                        ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                            ol_tag_for_inner_number)
                                        ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                        caps_alpha = "A"
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                inner_alphabet = 'a'
                elif re.search(fr'^\({number}\)|^\({inner_num}\)', tag.text.strip()):
                    if re.search(fr'^\({number}\) \({inner_alphabet}\) \({roman_number}\)', tag.text.strip()):
                        h3_id = tag.find_previous_sibling("h3").attrs['id']
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({number}\) \({alphabet}{alphabet}?\) \({roman_number}\)', '',
                                            tag.text.strip())
                        tag.wrap(ol_tag_for_roman)
                        li_tag_for_number = self.soup.new_tag("li")
                        li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{number}"
                        li_tag_for_number['class'] = "number"
                        li_tag_for_inner_alphabet = self.soup.new_tag("li")
                        li_tag_for_inner_alphabet['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}"
                        li_tag_for_inner_alphabet['class'] = "inner_alpha"
                        ol_tag_for_roman.wrap(li_tag_for_inner_alphabet)
                        li_tag_for_inner_alphabet.wrap(ol_tag_for_inner_alphabet)
                        ol_tag_for_inner_alphabet.wrap(li_tag_for_number)
                        li_tag_for_number.wrap(ol_tag_for_number)
                        tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}-{roman_number}"
                        tag['class'] = "roman"
                        number += 1
                        inner_alphabet = chr(ord(inner_alphabet) + 1)
                        roman_number = roman.fromRoman(roman_number.upper())
                        roman_number += 1
                        roman_number = roman.toRoman(roman_number).lower()
                    elif re.search(fr'^\({number}\) \({roman_number}\)', tag.text.strip()):
                        if re.search(fr'^\({number}\) \({roman_number}\) \({caps_alpha}{caps_alpha}?\)',
                                     tag.text.strip()):
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            caps_alpha_id = re.search(fr'\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                      tag.text.strip()).group('caps_alpha_id')
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({number}\) \({roman_number}\) \({caps_alpha}{caps_alpha}?\)', '',
                                                tag.text.strip())
                            tag.wrap(ol_tag_for_caps_alphabet)
                            tag['class'] = "caps_alpha"
                            li_tag_for_number = self.soup.new_tag("li")
                            li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{number}"
                            li_tag_for_roman = self.soup.new_tag("li")
                            li_tag_for_roman['id'] = f"{h3_id}ol{ol_count}{number}-{roman_number}"
                            li_tag_for_number['class'] = "number"
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}-{roman_number}-{caps_alpha_id}"
                            li_tag_for_roman['class'] = "roman"
                            li_tag_for_roman.append(ol_tag_for_caps_alphabet)
                            ol_tag_for_roman.append(li_tag_for_roman)
                            li_tag_for_number.append(ol_tag_for_roman)
                            ol_tag_for_number.append(li_tag_for_number)
                            number += 1
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            if caps_alpha == 'Z':
                                caps_alpha = 'A'
                            else:
                                caps_alpha = chr(ord(caps_alpha) + 1)
                        else:
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({number}\) \({roman_number}\)', '', tag.text.strip())
                            tag.wrap(ol_tag_for_roman)
                            li_tag = self.soup.new_tag("li")
                            li_tag['class'] = "number"
                            ol_tag_for_roman.wrap(li_tag)
                            if ol_tag_for_alphabet.li:
                                tag.attrs[
                                    'id'] = f"{ol_tag_for_alphabet.find_all('li', class_='alphabet')[-1].attrs['id']}{number}-{roman_number}"
                                li_tag[
                                    'id'] = f"{ol_tag_for_alphabet.find_all('li', class_='alphabet')[-1].attrs['id']}{number}"
                            else:
                                tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}-{roman_number}"
                                li_tag['id'] = f"{h3_id}ol{ol_count}{number}"
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            tag['class'] = "roman"
                            if ol_tag_for_number.li:
                                ol_tag_for_number.append(li_tag)
                            else:
                                li_tag.wrap(ol_tag_for_number)
                            number += 1

                            while next_tag.name != "h4" and next_tag.name != "h3" and (
                                    re.search(r'^“?[a-z A-Z]+|^\([0-9]+\)', next_tag.text.strip()) or (
                                    next_tag.next_element and next_tag.next_element.name == "br")):
                                if next_tag.next_element.name == "br":
                                    next_tag = self.decompose_break_tag(next_tag)
                                elif re.search("^“?[a-z A-Z]+", next_tag.text.strip()):
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                elif re.search(r"^\([0-9]+\)", next_tag.text.strip()):
                                    number_id = re.search(r"^\((?P<number_id>[0-9]+)\)", next_tag.text.strip()).group(
                                        'number_id')
                                    if number_id != str(number) and number_id != str(inner_num):
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                            count_of_p_tag = 1
                            if re.search(fr'^\({number}\)', next_tag.text.strip()):
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_roman)
                                ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                roman_number = "i"
                    elif re.search(fr'^\({number}\) \({inner_alphabet}\)', tag.text.strip()):
                        if re.search(fr'^\({number}\) \({inner_alphabet}\) \({roman_number}\)', tag.text.strip()):
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({number}\) \({inner_alphabet}\) \({roman_number}\)', '',
                                                tag.text.strip())
                            tag.wrap(ol_tag_for_roman)
                            li_tag_for_number = self.soup.new_tag("li")
                            li_tag_for_number['id'] = f"{h3_id}ol{ol_count}{number}"
                            li_tag_for_number['class'] = "number"
                            li_tag_for_inner_alphabet = self.soup.new_tag("li")
                            li_tag_for_inner_alphabet['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}"
                            li_tag_for_inner_alphabet['class'] = "inner_alpha"
                            tag.attrs['id'] = f"{h3_id}ol{ol_count}{number}{inner_alphabet}-{roman_number}"
                            li_tag_for_inner_alphabet.append(ol_tag_for_roman)
                            ol_tag_for_inner_alphabet.append(li_tag_for_inner_alphabet)
                            li_tag_for_number.append(ol_tag_for_inner_alphabet)
                            ol_tag_for_number.append(li_tag_for_number)
                            number += 1
                            roman_number = roman.fromRoman(roman_number.upper())
                            roman_number += 1
                            roman_number = roman.toRoman(roman_number).lower()
                            inner_alphabet = chr(ord(inner_alphabet) + 1)
                        elif re.search(fr'^\({number}\) \({inner_alphabet}\)', tag.text.strip()):
                            h3_id = tag.find_previous_sibling("h3").attrs['id']
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({number}\) \({inner_alphabet}\)', '', tag.text.strip())
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
                            if re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()):
                                ol_tag_for_number.find_all("li", class_="number")[-1].append(ol_tag_for_inner_alphabet)
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_inner_alphabet = self.soup.new_tag("ol", type="a")
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                                inner_alphabet = 'a'
                    elif re.search(fr'^\({number}\) \({caps_alpha}{caps_alpha}?\)', tag.text.strip()):

                        caps_alpha_id = re.search(fr'\((?P<caps_alpha_id>{caps_alpha}{caps_alpha}?)\)',
                                                  tag.text.strip()).group('caps_alpha_id')
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({number}\) \({caps_alpha}{caps_alpha}?\)', '', tag.text.strip())
                        tag['class'] = "caps_alpha"
                        li_tag = self.soup.new_tag("li")
                        if ol_tag_for_alphabet.li:
                            li_tag[
                                'id'] = f'{ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs["id"]}{number}'
                            tag.attrs[
                                'id'] = f'{ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs["id"]}{number}-{caps_alpha_id}'
                        else:
                            li_tag['id'] = f"{tag.find_previous_sibling('h3').attrs['id']}ol{ol_count}{number}"
                            tag.attrs[
                                'id'] = f"{tag.find_previous_sibling('h3').attrs['id']}ol{ol_count}{number}-{caps_alpha_id}"
                        li_tag['class'] = "number"
                        tag.wrap(ol_tag_for_caps_alphabet)
                        li_tag.append(ol_tag_for_caps_alphabet)

                        if caps_alpha == 'Z':
                            caps_alpha = 'A'
                        else:
                            caps_alpha = chr(ord(caps_alpha) + 1)
                        ol_tag_for_number.append(li_tag)
                        number += 1
                    elif re.search(fr'^\({number}\)',
                                   tag.text.strip()) and inner_num == 1 and not ol_tag_for_roman.li and not ol_tag_for_caps_alphabet.li:
                        tag.name = "li"
                        tag.string = re.sub(fr'^\({number}\)', '', tag.text.strip())
                        tag['class'] = "number"
                        if ol_tag_for_alphabet.li:
                            id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].attrs['id']
                            tag['id'] = f"{id_of_last_li}{number}"
                        elif ol_tag_for_caps_alphabet.li:
                            id_of_last_li = ol_tag_for_alphabet.find_all("li", class_="caps_alpha")[-1].attrs['id']
                            tag['id'] = f"{id_of_last_li}{number}"
                        else:
                            tag[
                                'id'] = f"{tag.find_previous(['h5', 'h4', 'h3'], ['notes_section', 'schedule', 'comment', 'section', 'article_h3']).get('id')}ol{ol_count}{number}"
                        if ol_tag_for_number.li:
                            ol_tag_for_number.append(tag)
                        else:
                            tag.wrap(ol_tag_for_number)
                        number += 1
                        while next_tag.name != "h4" and next_tag.name != "h5" and next_tag.name != "h3" and (re.search(
                                r"^\([A-Z a-z]+\)\.”|^\. \. \.|^\[See .*]|^“?[a-z A-Z]+|^_______________|^\((ix|iv|v?i{0,3})\)|^\([0-9]\)|^\([a-z]+\)|^\([A-Z ]+\)",
                                next_tag.text.strip()) or (
                                                                                                                     next_tag.next_element and next_tag.next_element.name == "br")):
                            if next_tag.next_element.name == "br":
                                next_tag = self.decompose_break_tag(next_tag)
                            elif re.search(
                                    r"^\([A-Z a-z]+\)\.”|^_______________|^\. \. \.|^\([a-z]+\)|^“?[a-z A-Z]+|^\[See .*]|^\([0-9]+\)|^\((ix|iv|v?i{0,3})\)|^\([A-Z ]+\) ",
                                    next_tag.text.strip()):
                                if re.search(r'^Section \d+', next_tag.text.strip()):
                                    break
                                elif re.search(
                                        r"^\([A-Z a-z]+\)\.”|^_______________|^\. \. \.|^\[See .*]|^“?[a-z A-Z]+",
                                        next_tag.text.strip()):
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                elif re.search(r'^\([0-9]+\)', next_tag.text.strip()):
                                    number_id = re.search(r'^\((?P<number_id>([0-9]+))\)', next_tag.text.strip()).group(
                                        'number_id')
                                    if number_id != str(number) and number_id != str(inner_num):
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                                elif re.search(r'^\([a-z]+\)', next_tag.text.strip()):
                                    alphabet_id = re.search(r'^\((?P<alphabet_id>([a-z]+))\)',
                                                            next_tag.text.strip()).group('alphabet_id')
                                    if alphabet_id[0] != alphabet and alphabet_id[0] != inner_alphabet and alphabet_id != roman_number and alphabet_id != inner_roman:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break

                                elif re.search(r'^\([A-Z ]+\) ', next_tag.text.strip()):
                                    alphabet_id = re.search(r'^\((?P<alphabet_id>([A-Z ]+))\)',
                                                            next_tag.text.strip()).group('alphabet_id')
                                    if alphabet_id != caps_alpha and alphabet_id != caps_roman and alphabet_id != inner_caps_roman:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                        count_of_p_tag = 1
                        if re.search(r'^Section \d+', next_tag.text.strip()):
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                            if re.search(r'^\(a\)|^\(\d\)', next_tag.find_next_sibling().text.strip()):
                                ol_count += 1
                        elif re.search('^ARTICLE [IVXCL]+', next_tag.text.strip()):
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                            ol_count = 1
                        elif re.search(fr'^\({alphabet}{alphabet}?\) \(1\) \({roman_number}\)', next_tag.text.strip()):
                            '''(h)(1)
                                  (2)
                               (i)(1)(i)
                                      (ii)
                            '''
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                        elif re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()):
                            if alphabet == 'i' and re.search(r'^\(ii\)|^\(B\)',
                                                             next_tag.find_next_sibling().text.strip()):
                                continue
                            elif ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_number = self.soup.new_tag("ol")
                                number = 1
                        elif next_tag.name == "h4" or next_tag.name == "h3" or next_tag.name == "h5":
                            if ol_tag_for_alphabet.li:
                                ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                alphabet = 'a'
                            ol_tag_for_number = self.soup.new_tag("ol")
                            number = 1
                    elif re.search(fr'^\({inner_num}\)', tag.text.strip()):
                        if re.search(fr'^\({inner_num}\) \({inner_roman}\)', tag.text.strip()):
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({inner_num}\) \({inner_roman}\)', '', tag.text.strip())
                            tag.wrap(ol_tag_for_inner_roman)
                            tag['class'] = "inner_roman"
                            li_tag = self.soup.new_tag("li")
                            if ol_tag_for_caps_alphabet.li:
                                id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs[
                                    'id']
                                li_tag['id'] = f"{id_of_last_li}{inner_num}"
                                tag.attrs[
                                    'id'] = f'{ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs["id"]}{inner_num}-{inner_roman}'
                            elif ol_tag_for_inner_alphabet.li:
                                id_of_last_li = ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs['id']
                                li_tag['id'] = f"{id_of_last_li}{inner_num}"
                                tag.attrs[
                                    'id'] = f'{ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].attrs["id"]}{inner_num}-{inner_roman}'
                            elif ol_tag_for_number.li:
                                id_of_last_li = ol_tag_for_number.find_all("li", class_="number")[-1].attrs['id']
                                li_tag['id'] = f"{id_of_last_li}{inner_num}"
                                tag.attrs[
                                    'id'] = f"{ol_tag_for_number.find_all('li', class_='number')[-1].attrs['id']}{inner_num}-{inner_roman}"

                            li_tag['class'] = "inner_num"
                            li_tag.append(ol_tag_for_inner_roman)
                            inner_roman = roman.fromRoman(inner_roman.upper())
                            inner_roman += 1
                            inner_roman = roman.toRoman(inner_roman).lower()
                            ol_tag_for_inner_number.append(li_tag)
                            inner_num += 1
                        else:
                            tag.name = "li"
                            tag.string = re.sub(fr'^\({inner_num}\)', '', tag.text.strip())
                            if ol_tag_for_inner_roman.li:
                                id_of_last_li = ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].attrs[
                                    'id']
                            elif ol_tag_for_caps_alphabet.li:
                                id_of_last_li = ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].attrs[
                                    'id']

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
                            while next_tag.name != "h4" and next_tag.name != "h3" and not re.search(
                                    '^ARTICLE [IVXCL]+', next_tag.text.strip(),
                                    re.IGNORECASE) and (re.search(r"^“?[a-z A-Z]+|^\([a-z]+\)|^\((ix|iv|v?i{0,3})\)",
                                                                  next_tag.text.strip()) or (
                                                                next_tag.next_element and next_tag.next_element.name == "br")):
                                if next_tag.next_element.name == "br":
                                    next_tag = self.decompose_break_tag(next_tag)
                                elif re.search(fr'^{inner_alphabet}\.|^{caps_alpha}{caps_alpha}?\.',
                                               next_tag.text.strip()):
                                    break
                                elif re.search("^“?[a-z A-Z]+", next_tag.text.strip()):
                                    next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                elif re.search(r'^\([a-z]+\)', next_tag.text.strip()):
                                    alphabet_id = re.search(r'^\((?P<alphabet_id>([a-z]+))\)',
                                                            next_tag.text.strip()).group(
                                        'alphabet_id')
                                    if alphabet_id[0] != alphabet and alphabet_id[0] != inner_alphabet and alphabet_id != roman_number and alphabet_id != inner_roman:
                                        next_tag, count_of_p_tag = self.add_p_tag_to_li(tag, next_tag, count_of_p_tag)
                                    else:
                                        break
                            count_of_p_tag = 1
                            if re.search(fr'^\({roman_number}\)',
                                         next_tag.text.strip()) and roman_number != "i":
                                if ol_tag_for_caps_alphabet.li:
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_caps_alphabet)
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type='A')
                                    caps_alpha = 'A'
                                else:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_inner_number)
                                    ol_tag_for_inner_number = self.soup.new_tag("ol")
                                    inner_num = 1
                            elif re.search(fr'^\({inner_roman}\)', next_tag.text.strip()) and inner_roman != "i":
                                ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].append(
                                    ol_tag_for_inner_number)
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1
                            elif re.search(fr'^\({caps_alpha}{caps_alpha}?\)', next_tag.text.strip()):
                                if ol_tag_for_caps_roman.li:
                                    ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_caps_roman)
                                    ol_tag_for_caps_roman = self.soup.new_tag("ol", type="I")
                                    caps_roman = "I"
                                elif ol_tag_for_inner_roman.li:
                                    ol_tag_for_inner_roman.find_all("li", class_="inner_roman")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_roman)
                                    ol_tag_for_inner_roman = self.soup.new_tag("ol", type="i")
                                    inner_roman = "i"
                                else:

                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1
                            elif re.search(fr'^\({caps_roman}\)', next_tag.text.strip()):
                                ol_tag_for_caps_roman.find_all("li", class_="caps_roman")[-1].append(
                                    ol_tag_for_inner_number)
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1
                            elif re.search(fr'^\({inner_alphabet}\)|^{inner_alphabet}\.',
                                           next_tag.text.strip()) and inner_alphabet != "a":
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_inner_number)
                                    ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                        ol_tag_for_roman)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                elif ol_tag_for_inner_alphabet.li:
                                    ol_tag_for_inner_alphabet.find_all("li", class_="inner_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1
                            elif re.search(fr'^\({alphabet}{alphabet}?\)', next_tag.text.strip()) and alphabet != 'a':
                                if ol_tag_for_roman.li:
                                    ol_tag_for_roman.find_all("li", class_="roman")[-1].append(ol_tag_for_inner_number)
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_roman)
                                    ol_tag_for_roman = self.soup.new_tag("ol", type="i")
                                    roman_number = "i"
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(ol_tag_for_number)
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1

                            elif re.search('^ARTICLE [IVXCL]+', next_tag.text.strip(),
                                           re.IGNORECASE):
                                if ol_tag_for_caps_alphabet.li:
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = "A"
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_number)
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1
                            elif next_tag.name == "h4" or next_tag.name == "h3":
                                if ol_tag_for_caps_alphabet.li:
                                    ol_tag_for_caps_alphabet.find_all("li", class_="caps_alpha")[-1].append(
                                        ol_tag_for_inner_number)
                                    if ol_tag_for_number.li:
                                        ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                            ol_tag_for_caps_alphabet)
                                        if ol_tag_for_alphabet.li:
                                            ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                                ol_tag_for_number)
                                            ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                            alphabet = "a"
                                        ol_tag_for_number = self.soup.new_tag("ol")
                                        number = 1
                                    ol_tag_for_caps_alphabet = self.soup.new_tag("ol", type="A")
                                    caps_alpha = "A"
                                elif ol_tag_for_number.li:
                                    ol_tag_for_number.find_all("li", class_="number")[-1].append(
                                        ol_tag_for_inner_number)
                                    if ol_tag_for_alphabet.li:
                                        ol_tag_for_alphabet.find_all("li", class_="alphabet")[-1].append(
                                            ol_tag_for_number)
                                        ol_tag_for_alphabet = self.soup.new_tag("ol", type="a")
                                        alphabet = "a"
                                    ol_tag_for_number = self.soup.new_tag("ol")
                                    number = 1
                                ol_tag_for_inner_number = self.soup.new_tag("ol")
                                inner_num = 1

    def add_citation(self):
        for tag in self.soup.find_all(["p", "li"]):
            if tag['class'] not in ["notes_to_decision", "notes_section", "notes_sub_section", "nav_li"]:
                tag_string = ''
                text = str(tag)
                text = re.sub('^<p[^>]*>|</p>$|^<li[^>]*>|</li>$', '', text.strip())
                cite_tag_pattern = {
                    'ri_const': r'(R\.I\. Const\.,? ((Decl\. Rights )?(art\.|article|Art\.|Article)( \d+| ?[IVXCL]+) ?((\. |, )?(Sec\.|§{1,2})\s+(\d+|[IVXCL]+))?)?)',
                    'ri': r'(\d+ R\.I\. \d+)',
                    'ri_lexis': r'(\d+ R\.I\. LEXIS \d+)',
                    'rir': r'(R\.I\. R\. Evid\. \d+)',
                    'ricr': '(230-RICR-30-10-1)',
                    'econ': r'(R\.I\. Econ\. Dev\. Corp\. v\. Parking Co\.)',
                    'gen_law': r'(R\.I\. Gen\. Laws)',
                    'airport_corp': r'(R\.I\. Airport Corp\.)',
                    'ri_const_amend': r'(R\.I\. Const\.,? (Amend|amend)\.,? (Art\. )?(\d+|[IVXCL]+)(, (Sec\.|§{1,2}) \d+)?)',
                    'ri_ct_r': r'(R\.I\. Super\. Ct\. R\. (Civ|Crim)\. P\. \d+(\. State v\. Long)?)'
                }

                for key in cite_tag_pattern:
                    cite_pattern = cite_tag_pattern[key]
                    if re.search(cite_pattern, tag.text.strip()):
                        for cite_pattern in set(
                                match[0] for match in re.findall('(' + cite_pattern + ')', tag.text.strip())):
                            target = "_self"
                            if self.html_file != 'gov.ri.code.constitution.ri.html':
                                a_id = 'gov.ri.code.constitution.ri.html'
                                target = "_blank"
                            else:
                                a_id = ''
                            if re.search(
                                    r'(R\.I\. Const\.,? (art\.|article|Art\.|Article) ?[IVXCL]+ ?[.,]? (Sec\.|§{1,2})\s+\d+)',
                                    cite_pattern):
                                ri_art = re.search(
                                    r'(R\.I\. Const\.,? (art\.|article|Art\.|Article) ?(?P<art_num>[CLXVI]+) ?[.,]? (Sec\.|§{1,2})\s+(?P<sec_num>\d+))',
                                    cite_pattern)
                                tag_id = f"tConstitutionoftheState-Article{ri_art.group('art_num')}s{ri_art.group('sec_num').zfill(2)}"
                                a_id = f'{a_id}#{tag_id}'
                                tag_string = re.sub(fr'{ri_art.group()}',
                                                    f'<cite class="ocri"><a href="{a_id}" target="{target}">{ri_art.group()}</a></cite>',
                                                    text)
                            elif re.search(
                                    r'(R\.I\. Const\.,? (art\.|article|Art\.|Article)( ?[IVXCL]+) ?(?!([IVXCL]+|\d+)? ?(\. |, )?(Sec\.|§{1,2})\s+(\d+|[IVXCL]+)))',
                                    cite_pattern):
                                ri_art = re.search(
                                    r'(R\.I\. Const\.,? (art\.|article|Art\.|Article) ?(?P<art_num>([IVXCL]+)) ?(?!([IVXCL]+|\d+)? ?(\. |, )?(Sec\.|§{1,2})\s+(\d+|[IVXCL]+)))',
                                    cite_pattern)
                                tag_id = f"tConstitutionoftheState-Article{ri_art.group('art_num').strip()}"
                                a_id = f'{a_id}#{tag_id}'
                                tag_string = re.sub(
                                    fr'\s{re.escape(ri_art.group())}' + r'(?!([IVXCL]+|\d+)? ?(\. |, )?(Sec\.|§{1,2})\s+(\d+|[IVXCL]+))',
                                    f'<cite class="ocri"><a href="{a_id}" target="{target}">{ri_art.group()}</a></cite>',
                                    text)
                            elif re.search(
                                    r'(R\.I\. Const\.,? (?!(Decl\. Rights )?((Amend|amend)\.,?( [Aa]rt\.?)?)?(art.|article|Art\.|Article)?( \d+| ?[IVXCL]+) ?((\. |, )?(Sec\.|§{1,2})\s+(\d+|[IVXCL]+))?))',
                                    cite_pattern):
                                ri_art = re.search(
                                    r'(R\.I\. Const\.,? (?!(Decl\. Rights )?((Amend|amend)\.,?( [Aa]rt\.?)?)?(art\.|article|Art\.|Article)?( \d+| ?[IVXCL]+) ?((\. |, )?(Sec\.|§{1,2})\s+(\d+|[IVXCL]+))?))',
                                    cite_pattern)
                                tag_id = f"tConstitutionoftheState"
                                a_id = f'{a_id}#{tag_id}'
                                tag_string = re.sub(
                                    fr'\s{re.escape(ri_art.group())}' + r'(?!(Decl\. Rights )?((Amend|amend)\.,?( [Aa]rt\.?)?)?(art.|article|Art\.|Article)?( \d+| ?[IVXCL]+) ?((\. |, )?(Sec\.|§{1,2})\s+(\d+|[IVXCL]+))?)',
                                    f'<cite class="ocri"><a href="{a_id}" target="{target}">{ri_art.group()}</a></cite>',
                                    text)
                            else:
                                tag_string = re.sub(cite_pattern, f'<cite class="ocri">{cite_pattern}</cite>', text)
                            text = tag_string

                if re.search(
                        r'\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?(( ?\([a-z0-9A-Z]+\) ?)+)?',
                        tag.text.strip()):
                    for pattern in sorted(set(match[0] for match in re.findall(
                            r'(\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?(( ?\([a-z0-9A-Z]+\) ?)+)?)',
                            tag.text.strip()))):
                        section_match = re.search(
                            r"(?P<section_id>(?P<title_id>\d+[A-Z]?(\.\d+)?)-(?P<chapter_id>\d+)(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?)",
                            pattern)
                        if re.search('A', section_match.group('title_id')):
                            title_id = f"{section_match.group('title_id').zfill(3)}"
                        else:
                            title_id = f"{section_match.group('title_id').zfill(2)}"
                        if exists(
                                f"../../cic-code-ri-1/transforms/ri/ocri/r{self.release_number}/gov.ri.code.title.{title_id}.html"):
                            file = open(
                                f"../../cic-code-ri-1/transforms/ri/ocri/r{self.release_number}/gov.ri.code.title.{title_id}.html")
                            content = file.read()
                            file.close()
                        else:
                            continue
                        target = "_self"
                        if section_match.group('title_id') != self.title:
                            a_id = f'gov.ri.code.title.{title_id}.html'
                            target = "_blank"
                        else:
                            a_id = ''
                        if re.search(
                                fr'\d+[A-Z]?(\.\d+)?-\d+(-\d+)?(([A-Z])(-\d+)?)?(\.\d+(-\d+)?(\.\d+((\.\d+)?\.\d+)?)?(-\d+)?)?( ?\([a-z0-9A-Z]+\) ?)+',
                                pattern.strip()):
                            match = re.search(fr'( ?\([a-z0-9A-Z]+\) ?)+', pattern.strip()).group()
                            match = re.sub(r'[()]', '', match)
                            if re.search('(?<!-)[A-Z]', match):
                                id_of_ol = re.search('(?P<id_of_ol>((?<!-)[A-Z]))', match).group('id_of_ol')
                                match = match.replace(id_of_ol, f'-{id_of_ol}')
                            if re.search('(?<!-)[IVXL]+', match):
                                id_of_ol = re.search('(?P<id_of_ol>[IVXL]+)', match).group('id_of_ol')
                                match = match.replace(id_of_ol, f'-{id_of_ol}')
                            section_id = section_match.group('section_id')
                            if re.search(fr'id=".+s{section_id}ol1{match}"', content):
                                tag_id = re.search(fr'id="(?P<tag_id>(.+s{section_id}ol1{match}))"', content).group(
                                    'tag_id')
                                a_id = f'{a_id}#{tag_id}'
                                tag_string = re.sub(fr'(\s|—){re.escape(pattern)}' + r'(?!( ?\([a-z0-9A-Z]+\) ?)+)',
                                                    f'<cite class="ocri"><a href="{a_id}" target="{target}">{pattern}</a></cite>',
                                                    text)
                        elif re.search(r'\d+[A-Z]?(\.\d+)?-\d+-\d+\.\d+(?!(\d+)?(\.\d+|\()|(( ?\([a-z0-9A-Z]+\) ?)+))',
                                       pattern):  # 21-28-4.07
                            if re.search(fr'id=".+s{pattern}"', content):
                                tag_id = re.search(fr'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                a_id = f'{a_id}#{tag_id}'
                                tag_string = re.sub(
                                    fr'(\s|—){re.escape(pattern)}' + r'(?!(\d+)?(\.\d+|\d+|\()|(( ?\([a-z0-9A-Z]+\) ?)+))',
                                    f'<cite class="ocri"><a href="{a_id}" target="{target}">{pattern}</a></cite>',
                                    text)
                        elif re.search(r'\d+[A-Z]?(\.\d+)?-\d+-\d+\.\d+\.\d+(?!(\d+)?( ?\([a-z0-9A-Z]+\) ?)+)',
                                       pattern):  # 21-28-4.07.1
                            if re.search(fr'id=".+s{pattern}"', content):
                                tag_id = re.search(fr'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                a_id = f'{a_id}#{tag_id}'
                                tag_string = re.sub(
                                    fr'(\s|—){re.escape(pattern)}' + r'(?!((\d+)?( ?\([a-z0-9A-Z]+\) ?)+)|(\d+))',
                                    f'<cite class="ocri"><a href="{a_id}" target="{target}" >{pattern}</a></cite>',
                                    text)
                        else:
                            if re.search(
                                    r'(?<!\d)(?<![.-])\d+[A-Z]?(\.\d+)?-\d+(?!(\d+)?((\.\d+)|(-\d+)|(( ?\([a-z0-9A-Z]+\) ?)+)|([a-zA-Z])))',
                                    pattern):  # 12-32
                                chapter_id = section_match.group('chapter_id').zfill(2)
                                if re.search(fr'id=".+c{chapter_id}"', content):
                                    tag_id = re.search(fr'id="(?P<tag_id>(.+c{chapter_id}))"', content).group('tag_id')
                                    a_id = f'{a_id}#{tag_id}'
                                    tag_string = re.sub(
                                        fr'(\s|—){re.escape(pattern)}' + r'(?!(\d+)?((\.\d+)|(-\d+)|(\d+)|(( ?\([a-z0-9A-Z]+\) ?)+)|([a-zA-Z])))',
                                        f'<cite class="ocri"><a href="{a_id}" target="{target}" >{pattern}</a></cite>',
                                        text)
                            else:
                                if re.search(
                                        r'\d+[A-Z]?(\.\d+)?-\d+(([A-Z])(-\d+)?)?-\d(?!((\d+)?(\.\d+|(\d+)|(-\d+)|( ?\([a-z0-9A-Z]+\) ?)+)))',
                                        pattern):
                                    if re.search(fr'id=".+s{pattern}"', content):
                                        tag_id = re.search(fr'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        a_id = f'{a_id}#{tag_id}'
                                        tag_string = re.sub(
                                            fr'(\s|—){re.escape(pattern)}' + r'(?!((\d+)?((\.\d+)|(-\d+)|(\d+)|( ?\([a-z0-9A-Z]+\) ?)+)))',
                                            f'<cite class="ocri"><a href="{a_id}" target="{target}" >{pattern}</a></cite>',
                                            text)

                                elif re.search(
                                        r'\d+[A-Z]?(\.\d+)?-\d+-\d+(?!((\d+)?(\.\d+|(\d+)|-\d+|( ?\([a-z0-9A-Z]+\) ?)+)))',
                                        pattern):
                                    if re.search(fr'id=".+s{pattern}"', content):
                                        tag_id = re.search(fr'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        a_id = f'{a_id}#{tag_id}'
                                        tag_string = re.sub(
                                            fr'(\s|—){re.escape(pattern)}' + r'(?!((\d+)?((\.\d+)|(\d+)|(-\d+)|( ?\([a-z0-9A-Z]+\) ?)+)))',
                                            f'<cite class="ocri"><a href="{a_id}" target="{target}" >{pattern}</a></cite>',
                                            text)

                                elif re.search(
                                        r'\d+[A-Z]?(\.\d+)?-\d+\.\d+(\.\d+)?-\d(?!(\d+))(?!\.\d+)(?!( ?\([a-z0-9A-Z]+\) ?)+)',
                                        pattern):
                                    if re.search(fr'id=".+s{pattern}"', content):
                                        tag_id = re.search(fr'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        a_id = f'{a_id}#{tag_id}'
                                        tag_string = re.sub(
                                            fr'(\s|—){re.escape(pattern)}' + r'(?!(\d+))(?!\.\d+)(?!( ?\([a-z0-9A-Z]+\) ?)+)',
                                            f'<cite class="ocri"><a href="{a_id}" target="{target}" >{pattern}</a></cite>',
                                            text)
                                elif re.search(
                                        r'\d+[A-Z]?(\.\d+)?-\d+\.\d+(\.\d+)?-\d(?!(\d+))\.\d+(?!( ?\([a-z0-9A-Z]+\) ?)+)',
                                        pattern):
                                    if re.search(fr'id=".+s{pattern}"', content):
                                        tag_id = re.search(fr'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        a_id = f'{a_id}#{tag_id}'
                                        tag_string = re.sub(
                                            fr'(\s|—){re.escape(pattern)}' + r'(?!((\d+)?( ?\([a-z0-9A-Z]+\) ?)+)|(\d+))',
                                            f'<cite class="ocri"><a href="{a_id}" target="{target}" >{pattern}</a></cite>',
                                            text)

                                elif re.search(
                                        r'\d+[A-Z]?(\.\d+)?-\d+\.\d+(\.\d+)?-\d+(?!(\d+))(\.\d+((\.\d+)?\.\d+)?)?(?!(\d+)?( ?\([a-z0-9A-Z]+\) ?)+)',
                                        pattern):  # 23-4.1-10
                                    if re.search(fr'id=".+s{pattern}"', content):
                                        tag_id = re.search(fr'id="(?P<tag_id>(.+s{pattern}))"', content).group('tag_id')
                                        a_id = f'{a_id}#{tag_id}'
                                        tag_string = re.sub(
                                            fr'(\s|—){re.escape(pattern)}' + r'(?!(\d+)?(( ?\([a-z0-9A-Z]+\) ?)+|(\d+)|\.\d+))',
                                            f'<cite class="ocri"><a href="{a_id}" target="{target}" >{pattern}</a></cite>',
                                            text)
                        if tag_string:
                            text = tag_string
                if tag_string:
                    tag_class = tag['class']
                    tag.clear()
                    tag.append(BeautifulSoup(tag_string, features="html.parser"))
                    tag['class'] = tag_class

    def create_div_tag(self):
        div_tag_for_chapter = self.soup.new_tag("div")
        div_tag_for_section = self.soup.new_tag("div")
        div_tag_for_h4 = self.soup.new_tag("div")
        div_tag_for_h5 = self.soup.new_tag("div")
        div_tag_for_article = self.soup.new_tag("div")
        div_tag_for_article_h2 = self.soup.new_tag("div")
        div_tag_for_part = self.soup.new_tag("div")
        div_tag_for_sub_part = self.soup.new_tag("div")
        for tag in self.soup.find_all("h2"):
            if re.search(r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?', tag.text.strip()):
                next_tag = tag.find_next_sibling()
                tag.wrap(div_tag_for_chapter)
                if next_tag.name == "nav":
                    sibling_of_nav = next_tag.find_next_sibling()
                    div_tag_for_chapter.append(next_tag)
                    next_tag = sibling_of_nav
                    while next_tag.name == "p":
                        sibling_of_p = next_tag.find_next_sibling()
                        div_tag_for_chapter.append(next_tag)
                        next_tag = sibling_of_p
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
                    elif next_tag.name == "h2" and re.search(r'^Part (\d{1,2}|[IVXCL]+)', next_tag.text.strip()):
                        sibling_of_h2 = next_tag.find_next_sibling()
                        div_tag_for_part.append(next_tag)
                        next_tag = sibling_of_h2
                        if next_tag.name == "nav":
                            sibling_of_nav = next_tag.find_next_sibling()
                            div_tag_for_part.append(next_tag)
                            next_tag = sibling_of_nav
                            if next_tag.name == "h2":
                                sibling_of_h2 = next_tag.find_next_sibling()
                                div_tag_for_sub_part.append(next_tag)
                                next_tag = sibling_of_h2
                                if next_tag.name == "nav":
                                    sibling_of_nav = next_tag.find_next_sibling()
                                    div_tag_for_sub_part.append(next_tag)
                                    next_tag = sibling_of_nav
                    elif next_tag.name == "h2" and re.search(r'^Article (\d+|[IVXCL]+)', next_tag.text.strip()):
                        sibling_of_h2 = next_tag.find_next_sibling()
                        div_tag_for_article_h2.append(next_tag)
                        next_tag = sibling_of_h2
                        if next_tag.name == "nav":
                            sibling_of_nav = next_tag.find_next_sibling()
                            div_tag_for_article_h2.append(next_tag)
                            next_tag = sibling_of_nav
                            if next_tag.name == "h2":
                                sibling_of_h2 = next_tag.find_next_sibling()
                                div_tag_for_part.append(next_tag)
                                next_tag = sibling_of_h2
                                if next_tag.name == "nav":
                                    sibling_of_nav = next_tag.find_next_sibling()
                                    div_tag_for_part.append(next_tag)
                                    next_tag = sibling_of_nav
                    if next_tag.name == "h3":
                        tag_of_h3 = next_tag.find_next_sibling()
                        if re.search(r'^ARTICLE [IVXCL]+|^Article \d+\.', next_tag.text.strip(),
                                     re.IGNORECASE):
                            next_tag.wrap(div_tag_for_article)
                        else:
                            next_tag.wrap(div_tag_for_section)
                        while tag_of_h3 and (tag_of_h3.name != "h2" or (
                                tag_of_h3.name == "h2" and not re.search(r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                                                         tag_of_h3.text.strip()))):
                            if tag_of_h3.name == "h4":
                                tag_of_h4 = tag_of_h3.find_next_sibling()
                                tag_of_h3.wrap(div_tag_for_h4)
                                next_tag = tag_of_h4
                                while tag_of_h4 and tag_of_h4.name != "h4" and (tag_of_h4.name != "h2" or (tag_of_h4.name == "h2" and not re.search(r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?', tag_of_h4.text.strip()))):
                                    if tag_of_h4.name == "h2":
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_section.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                            if re.search('^Subpart [A-Z0-9]', tag_of_h4.text.strip()):
                                                if div_tag_for_sub_part.li:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_sub_part.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_part.append(div_tag_for_sub_part)
                                                    div_tag_for_sub_part = self.soup.new_tag("div")
                                                else:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_sub_part.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_sub_part.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                    if tag_of_h4.name == "h3":
                                                        next_tag = tag_of_h4.find_next_sibling()
                                                        div_tag_for_section.append(tag_of_h4)
                                                        tag_of_h4 = next_tag
                                            elif re.search(r'^Part (\d{1,2}|[IVXCL]+)',
                                                           tag_of_h4.text.strip()):
                                                if div_tag_for_sub_part.li:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_sub_part.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_part.append(div_tag_for_sub_part)
                                                    div_tag_for_sub_part = self.soup.new_tag("div")
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                elif div_tag_for_part.next_element:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_part.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                else:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_part.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_part.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                    if tag_of_h4.name == "h2":
                                                        next_tag = tag_of_h4.find_next_sibling()
                                                        div_tag_for_sub_part.append(tag_of_h4)
                                                        tag_of_h4 = next_tag
                                                        if tag_of_h4.name == "nav":
                                                            next_tag = tag_of_h4.find_next_sibling()
                                                            div_tag_for_sub_part.append(tag_of_h4)
                                                            tag_of_h4 = next_tag
                                                            if tag_of_h4.name == "h3":
                                                                next_tag = tag_of_h4.find_next_sibling()
                                                                div_tag_for_section.append(tag_of_h4)
                                                                tag_of_h4 = next_tag
                                            elif re.search(r'^Article (\d+|[IVXCL]+)', tag_of_h4.text.strip()):
                                                next_tag = tag_of_h4.find_next_sibling()
                                                if div_tag_for_part.next_element:
                                                    div_tag_for_part.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                        div_tag_for_part = self.soup.new_tag("div")
                                                        div_tag_for_chapter.append(div_tag_for_article_h2)
                                                        div_tag_for_article_h2 = self.soup.new_tag("div")
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                        div_tag_for_part = self.soup.new_tag("div")
                                                elif div_tag_for_article_h2.next_element:
                                                    div_tag_for_article_h2.append(div_tag_for_section)
                                                    div_tag_for_chapter.append(div_tag_for_article_h2)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_article_h2 = self.soup.new_tag("div")
                                                else:
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_article_h2.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article_h2.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                    if tag_of_h4.name == "h2":
                                                        next_tag = tag_of_h4.find_next_sibling()
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
                                                    elif tag_of_h4.name == "h3":
                                                        next_tag = tag_of_h4.find_next_sibling()
                                                        div_tag_for_section.append(tag_of_h4)
                                                        tag_of_h4 = next_tag
                                    elif tag_of_h4.name == "h3":
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_section.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                        if re.search(r'^ARTICLE [IVXCL]+|^Article \d+\.',
                                                     tag_of_h4.text.strip(), re.IGNORECASE):
                                            next_tag = tag_of_h4.find_next_sibling()
                                            tag_of_h4.wrap(div_tag_for_article)
                                            tag_of_h4 = next_tag
                                            while tag_of_h4.name == "p" or (tag_of_h4.name == "h3" and re.search(
                                                    r'^ARTICLE [IVXCL]+|^Article \d+\.',
                                                    tag_of_h4.text.strip(), re.IGNORECASE)) or tag_of_h4.name == "ol":
                                                if tag_of_h4.name == "h3":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_section.append(div_tag_for_article)
                                                    div_tag_for_article = self.soup.new_tag("div")
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif tag_of_h4.next_element.name == "br":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    tag_of_h4 = next_tag
                                                elif tag_of_h4.name == "ol":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif tag_of_h4['class'][0] == self.dictionary_to_store_class_name['History']:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif re.search('^[A-Z a-z$0-9]+',
                                                               tag_of_h4.text.strip()) and tag_of_h4.name == "p":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                elif tag_of_h4['class'][0] == self.dictionary_to_store_class_name['h4']:
                                                    div_tag_for_section.append(div_tag_for_article)
                                                    div_tag_for_article = self.soup.new_tag("div")
                                                    break
                                            div_tag_for_section.append(div_tag_for_article)
                                            div_tag_for_article = self.soup.new_tag("div")
                                        else:
                                            if div_tag_for_section.next_element:
                                                if div_tag_for_sub_part.li:
                                                    div_tag_for_sub_part.append(div_tag_for_section)
                                                elif div_tag_for_part.next_element:
                                                    div_tag_for_part.append(div_tag_for_section)
                                                elif div_tag_for_article_h2.next_element:
                                                    div_tag_for_article_h2.append(div_tag_for_section)
                                                else:
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                            div_tag_for_section = self.soup.new_tag("div")
                                            next_tag = tag_of_h4.find_next_sibling()
                                            div_tag_for_section.append(tag_of_h4)
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
                                            elif tag_of_h5.name == "h2" and re.search(
                                                    r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
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
                                            elif tag_of_h5.name == "h2" and re.search(
                                                    r'^Part (\d{1,2}|[IVXCL]+)', tag_of_h5.text.strip()):
                                                next_tag = tag_of_h5.find_next_sibling()
                                                if div_tag_for_h5.next_element:
                                                    next_tag = tag_of_h5.find_next_sibling()
                                                    div_tag_for_h4.append(div_tag_for_h5)
                                                    div_tag_for_h5 = self.soup.new_tag("div")
                                                    div_tag_for_section.append(div_tag_for_h4)
                                                    div_tag_for_h4 = self.soup.new_tag("div")
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
                                            elif tag_of_h5.name == "h2" and re.search(r'^Article (\d+|[IVXCL]+)',
                                                                                      tag_of_h5.text.strip()):
                                                next_tag = tag_of_h5.find_next_sibling()
                                                if div_tag_for_h5.next_element:
                                                    next_tag = tag_of_h5.find_next_sibling()
                                                    div_tag_for_h4.append(div_tag_for_h5)
                                                    div_tag_for_h5 = self.soup.new_tag("div")
                                                    div_tag_for_section.append(div_tag_for_h4)
                                                    div_tag_for_h4 = self.soup.new_tag("div")
                                                if div_tag_for_part.next_element:
                                                    div_tag_for_part.append(div_tag_for_section)
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                        div_tag_for_chapter.append(div_tag_for_article_h2)
                                                        div_tag_for_article_h2 = self.soup.new_tag("div")
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                    div_tag_for_article_h2.append(tag_of_h5)
                                                    tag_of_h5 = next_tag
                                                    if tag_of_h5.name == "nav":
                                                        next_tag = tag_of_h5.find_next_sibling()
                                                        div_tag_for_part.append(tag_of_h5)
                                                        tag_of_h5 = next_tag
                                                        if tag_of_h5.name == "h3":
                                                            next_tag = tag_of_h5.find_next_sibling()
                                                            div_tag_for_section.append(tag_of_h5)
                                                            tag_of_h5 = next_tag
                                                elif div_tag_for_article_h2.next_element:
                                                    div_tag_for_article_h2.append(div_tag_for_section)
                                                    div_tag_for_chapter.append(div_tag_for_article_h2)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_article_h2 = self.soup.new_tag("div")
                                                    div_tag_for_article_h2.append(tag_of_h5)
                                                    tag_of_h5 = next_tag
                                                    if tag_of_h5.name == "nav":
                                                        next_tag = tag_of_h5.find_next_sibling()
                                                        div_tag_for_article_h2.append(tag_of_h5)
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
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_section.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                        div_tag_for_section.append(tag_of_h4)
                                        tag_of_h4 = next_tag
                                        if tag_of_h4.name == "h2" and re.search(
                                                r'^Chapters? \d+(\.\d+)?(\.\d+)?([A-Z])?',
                                                tag_of_h4.text.strip()):
                                            if div_tag_for_sub_part.next_element:
                                                div_tag_for_sub_part.append(div_tag_for_section)
                                                div_tag_for_part.append(div_tag_for_sub_part)
                                                div_tag_for_chapter.append(div_tag_for_part)
                                                div_tag_for_part = self.soup.new_tag("div")
                                                div_tag_for_sub_part = self.soup.new_tag("div")
                                            elif div_tag_for_part.next_element:
                                                div_tag_for_part.append(div_tag_for_section)
                                                div_tag_for_chapter.append(div_tag_for_part)
                                                div_tag_for_part = self.soup.new_tag("div")
                                            else:
                                                div_tag_for_chapter.append(div_tag_for_section)
                                            div_tag_for_section = self.soup.new_tag("div")
                                            div_tag_for_chapter = self.soup.new_tag("div")
                                        elif tag_of_h4.name == "h2":
                                            if re.search('^Subpart [A-Z0-9]', tag_of_h4.text.strip()):
                                                if div_tag_for_sub_part.li:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_sub_part.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_part.append(div_tag_for_sub_part)
                                                    div_tag_for_sub_part = self.soup.new_tag("div")
                                                else:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_sub_part.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_sub_part.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                    if tag_of_h4.name == "h3":
                                                        next_tag = tag_of_h4.find_next_sibling()
                                                        div_tag_for_section.append(tag_of_h4)
                                                        tag_of_h4 = next_tag
                                            elif re.search(r'^Part (\d{1,2}|[IVXCL]+)',
                                                           tag_of_h4.text.strip()):
                                                if div_tag_for_sub_part.next_element:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_sub_part.append(div_tag_for_section)
                                                    div_tag_for_part.append(div_tag_for_sub_part)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_sub_part = self.soup.new_tag("div")
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                elif div_tag_for_part.next_element:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_part.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                else:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_part.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_part.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                    if tag_of_h4.name == "h2":
                                                        next_tag = tag_of_h4.find_next_sibling()
                                                        div_tag_for_sub_part.append(tag_of_h4)
                                                        tag_of_h4 = next_tag
                                                        if tag_of_h4.name == "nav":
                                                            next_tag = tag_of_h4.find_next_sibling()
                                                            div_tag_for_sub_part.append(tag_of_h4)
                                                            tag_of_h4 = next_tag
                                                            if tag_of_h4.name == "h3":
                                                                next_tag = tag_of_h4.find_next_sibling()
                                                                div_tag_for_section.append(tag_of_h4)
                                                                tag_of_h4 = next_tag
                                            elif re.search(r'^Article (\d+|[IVXCL]+)', tag_of_h4.text.strip()):
                                                next_tag = tag_of_h4.find_next_sibling()
                                                if div_tag_for_sub_part.next_element:
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_sub_part.append(div_tag_for_section)
                                                    div_tag_for_part.append(div_tag_for_sub_part)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_sub_part = self.soup.new_tag("div")
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                        div_tag_for_chapter.append(div_tag_for_article_h2)
                                                        div_tag_for_article_h2 = self.soup.new_tag("div")
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                    div_tag_for_part = self.soup.new_tag("div")
                                                elif div_tag_for_part.next_element:
                                                    div_tag_for_part.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    if div_tag_for_article_h2.next_element:
                                                        div_tag_for_article_h2.append(div_tag_for_part)
                                                        div_tag_for_part = self.soup.new_tag("div")
                                                        div_tag_for_chapter.append(div_tag_for_article_h2)
                                                        div_tag_for_article_h2 = self.soup.new_tag("div")
                                                    else:
                                                        div_tag_for_chapter.append(div_tag_for_part)
                                                        div_tag_for_part = self.soup.new_tag("div")
                                                elif div_tag_for_article_h2.next_element:
                                                    div_tag_for_article_h2.append(div_tag_for_section)
                                                    div_tag_for_chapter.append(div_tag_for_article_h2)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                    div_tag_for_article_h2 = self.soup.new_tag("div")
                                                else:
                                                    div_tag_for_chapter.append(div_tag_for_section)
                                                    div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_article_h2.append(tag_of_h4)
                                                tag_of_h4 = next_tag
                                                if tag_of_h4.name == "nav":
                                                    next_tag = tag_of_h4.find_next_sibling()
                                                    div_tag_for_article_h2.append(tag_of_h4)
                                                    tag_of_h4 = next_tag
                                                    if tag_of_h4.name == "h2":
                                                        next_tag = tag_of_h4.find_next_sibling()
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
                                                    elif tag_of_h4.name == "h3":
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
                            elif tag_of_h3.name == "h3" and re.search(r'^ARTICLE [IVXCL]+|^Article \d+\.', tag_of_h3.text.strip(), re.IGNORECASE):
                                next_tag = tag_of_h3.find_next_sibling()
                                div_tag_for_article.append(tag_of_h3)
                                tag_of_h3 = next_tag
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
                            if div_tag_for_sub_part.li:
                                div_tag_for_sub_part.append(div_tag_for_section)
                                div_tag_for_part.append(div_tag_for_sub_part)
                                div_tag_for_chapter.append(div_tag_for_part)
                                div_tag_for_sub_part = self.soup.new_tag('div')
                                div_tag_for_part = self.soup.new_tag('div')
                            elif div_tag_for_part.next_element:
                                div_tag_for_part.append(div_tag_for_section)
                                if div_tag_for_article_h2.next_element:
                                    div_tag_for_article_h2.append(div_tag_for_part)
                                    div_tag_for_chapter.append(div_tag_for_article_h2)
                                    div_tag_for_article_h2 = self.soup.new_tag("div")
                                div_tag_for_chapter.append(div_tag_for_part)
                                div_tag_for_part = self.soup.new_tag('div')
                            elif div_tag_for_article_h2.next_element:
                                div_tag_for_article_h2.append(div_tag_for_section)
                                div_tag_for_chapter.append(div_tag_for_article_h2)
                                div_tag_for_article_h2 = self.soup.new_tag("div")
                            else:
                                div_tag_for_chapter.append(div_tag_for_section)
                            div_tag_for_section = self.soup.new_tag("div")
                            div_tag_for_chapter = self.soup.new_tag("div")

    def create_div_tag_for_constitution(self):
        div_tag_for_chapter = self.soup.new_tag("div")
        div_tag_for_section = self.soup.new_tag("div")
        div_tag_for_h4 = self.soup.new_tag("div")
        div_tag_for_h5 = self.soup.new_tag("div")
        div_tag_for_amendment = self.soup.new_tag("div")
        for tag in self.soup.find_all("h2"):
            if re.search('^Article [IVXCL]+|^Articles of Amendment|^Preamble',
                         tag.text.strip()):
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
                    elif next_tag.name == "p":
                        sibling_of_p = next_tag.find_next_sibling()
                        div_tag_for_chapter.append(next_tag)
                        next_tag = sibling_of_p
                    if next_tag.name == "h3":
                        tag_of_h3 = next_tag.find_next_sibling()
                        if re.search('^Amendment [IVXCL]+', next_tag.text.strip()):
                            next_tag.wrap(div_tag_for_amendment)
                        else:
                            next_tag.wrap(div_tag_for_section)
                        while tag_of_h3 and tag_of_h3.name != "h2":
                            if tag_of_h3.name == "h4":
                                tag_of_h4 = tag_of_h3.find_next_sibling()
                                tag_of_h3.wrap(div_tag_for_h4)
                                while tag_of_h4 and tag_of_h4.name != "h4" and tag_of_h4.name != "h2":
                                    if tag_of_h4.name == "h3" and re.search('^Amendment [IVXCL]+',
                                                                            tag_of_h4.text.strip()):
                                        if div_tag_for_h4.next_element:
                                            if div_tag_for_section.next_element:
                                                div_tag_for_section.append(div_tag_for_h4)
                                            else:
                                                div_tag_for_amendment.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                        if div_tag_for_section.next_element:
                                            if div_tag_for_amendment.next_element:
                                                div_tag_for_amendment.append(div_tag_for_section)
                                                div_tag_for_chapter.append(div_tag_for_amendment)
                                                div_tag_for_amendment = self.soup.new_tag("div")
                                            else:
                                                div_tag_for_chapter.append(div_tag_for_section)
                                        elif div_tag_for_amendment.next_element:
                                            div_tag_for_chapter.append(div_tag_for_amendment)
                                            div_tag_for_amendment = self.soup.new_tag("div")
                                        div_tag_for_section = self.soup.new_tag("div")
                                        next_tag = tag_of_h4.find_next_sibling()
                                        div_tag_for_amendment.append(tag_of_h4)
                                        tag_of_h4 = next_tag
                                        if tag_of_h4.name == "nav":
                                            next_tag = tag_of_h4.find_next_sibling()
                                            div_tag_for_amendment.append(tag_of_h4)
                                            tag_of_h4 = next_tag
                                        if tag_of_h4.name == "p":
                                            next_tag = tag_of_h4.find_next_sibling()
                                            div_tag_for_amendment.append(tag_of_h4)
                                            tag_of_h4 = next_tag
                                    elif tag_of_h4.name == "h3":
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_section.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                        if div_tag_for_section.next_element:
                                            if div_tag_for_amendment.next_element:
                                                div_tag_for_amendment.append(div_tag_for_section)
                                            else:
                                                div_tag_for_chapter.append(div_tag_for_section)
                                        div_tag_for_section = self.soup.new_tag("div")
                                        next_tag = tag_of_h4.find_next_sibling()
                                        div_tag_for_section.append(tag_of_h4)
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
                                            elif tag_of_h5.name == "h2" and re.search(
                                                    '^Article [IVXCL]+|^Articles of Amendment|^Preamble',
                                                    tag_of_h5.text.strip()):
                                                div_tag_for_chapter.append(div_tag_for_section)
                                                div_tag_for_section = self.soup.new_tag("div")
                                                div_tag_for_chapter = self.soup.new_tag("div")
                                                break
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
                                        if div_tag_for_h4.next_element:
                                            div_tag_for_section.append(div_tag_for_h4)
                                            div_tag_for_h4 = self.soup.new_tag("div")
                                        div_tag_for_section.append(tag_of_h4)
                                        tag_of_h4 = next_tag

                                        if tag_of_h4.name == "h2" and re.search(
                                                '^Article [IVXCL]+|^Articles of Amendment|^Preamble',
                                                tag_of_h4.text.strip()):
                                            div_tag_for_chapter.append(div_tag_for_section)
                                            div_tag_for_section = self.soup.new_tag("div")
                                            div_tag_for_chapter = self.soup.new_tag("div")
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
                                    if div_tag_for_section.next_element:
                                        div_tag_for_section.append(div_tag_for_h4)
                                    else:
                                        div_tag_for_amendment.append(div_tag_for_h4)
                                    div_tag_for_h4 = self.soup.new_tag("div")
                            elif tag_of_h3.name == "h3":
                                next_tag = tag_of_h3.find_next_sibling()
                                div_tag_for_section.append(tag_of_h3)
                            elif tag_of_h3.name == "p":
                                next_tag = tag_of_h3.find_next_sibling()
                                div_tag_for_section.append(tag_of_h3)
                            tag_of_h3 = next_tag

                        if div_tag_for_section.next_element:
                            if div_tag_for_amendment.next_element:
                                div_tag_for_amendment.append(div_tag_for_section)
                                div_tag_for_chapter.append(div_tag_for_amendment)
                                div_tag_for_amendment = self.soup.new_tag("div")
                            else:
                                div_tag_for_chapter.append(div_tag_for_section)
                            div_tag_for_section = self.soup.new_tag("div")
                            div_tag_for_chapter = self.soup.new_tag("div")
                        if div_tag_for_amendment.next_element:
                            div_tag_for_chapter.append(div_tag_for_amendment)
                            div_tag_for_amendment = self.soup.new_tag("div")
                            div_tag_for_chapter = self.soup.new_tag("div")

                elif next_tag.name == "p":
                    while next_tag.name == "p":
                        sibling_of_p = next_tag.find_next_sibling()
                        div_tag_for_chapter.append(next_tag)
                        next_tag = sibling_of_p
                    tag_of_h3 = next_tag
                    if tag_of_h3.name == "h4":
                        tag_of_h4 = tag_of_h3.find_next_sibling()
                        tag_of_h3.wrap(div_tag_for_h4)
                        while tag_of_h4.name != "h2":
                            if tag_of_h4.name == "h3":
                                if div_tag_for_h4.next_element:
                                    div_tag_for_section.append(div_tag_for_h4)
                                    div_tag_for_h4 = self.soup.new_tag("div")
                                if div_tag_for_section.next_element:
                                    div_tag_for_chapter.append(div_tag_for_section)
                                div_tag_for_section = self.soup.new_tag("div")
                                next_tag = tag_of_h4.find_next_sibling()
                                div_tag_for_section.append(tag_of_h4)
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
                                    elif tag_of_h5.name == "h2" and re.search(
                                            '^Article [IVXCL]+|^Articles of Amendment|^Preamble',
                                            tag_of_h5.text.strip()):
                                        if div_tag_for_h5.next_element:
                                            div_tag_for_h4.append(div_tag_for_h5)
                                            div_tag_for_h5 = self.soup.new_tag("div")
                                        break
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
                                if tag_of_h4.name == "h2" and re.search(
                                        '^Article [IVXCL]+|^Articles of Amendment|^Preamble',
                                        tag_of_h4.text.strip()):
                                    div_tag_for_chapter.append(div_tag_for_section)
                                    div_tag_for_section = self.soup.new_tag("div")
                                    div_tag_for_chapter = self.soup.new_tag("div")
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
                            elif tag_of_h4.name == "h4":
                                next_tag = tag_of_h4.find_next_sibling()
                                if div_tag_for_h4.next_element:
                                    if div_tag_for_section.next_element:
                                        div_tag_for_section.append(div_tag_for_h4)
                                    else:
                                        div_tag_for_chapter.append(div_tag_for_h4)
                                    div_tag_for_h4 = self.soup.new_tag("div")
                                div_tag_for_h4.append(tag_of_h4)
                                tag_of_h4 = next_tag
                        if div_tag_for_h4.next_element:
                            if div_tag_for_section.next_element:
                                div_tag_for_section.append(div_tag_for_h4)
                                div_tag_for_chapter.append(div_tag_for_section)
                                div_tag_for_section = self.soup.new_tag("div")
                            else:
                                div_tag_for_chapter.append(div_tag_for_h4)
                            div_tag_for_h4 = self.soup.new_tag("div")
                            div_tag_for_chapter = self.soup.new_tag("div")

    def remove_from_header_tag(self):
        list_to_remove_from_header_tag = ['text/css', 'LEXIS Publishing']
        for tag in self.soup.find_all('meta'):
            if tag['content'] in list_to_remove_from_header_tag:
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
            'content'] = f"Release {self.release_number} of the Official Code of Rhode Island Annotated released {self.release_date}.Transformed and posted by Public.Resource.Org using rtf-parser.py version 1.0 on {datetime.now().date()}.This document is not subject to copyright and is in the public domain. "
        self.soup.head.append(meta_tag)
        self.soup.head.append(meta_tag_for_water_mark)

    def cleanup(self):
        for tag in self.soup.body.find_all():
            if tag.name in ['li', 'h4', 'h3', 'p', 'h1', 'h5'] and tag['class'] != "transformation":
                del tag["class"]
            if tag.name == "span":
                tag.decompose()
            if not tag.text.strip():
                tag.decompose()

    def write_to_file(self):
        soup_text = str(self.soup.prettify())
        soup_text = soup_text.replace('/>', ' />')

        soup_text = re.sub('&(!?amp;)', '&amp;', soup_text)
        with open(f"../../cic-code-ri-1/transforms/ri/ocri/r{self.release_number}/{self.html_file}", "w") as file:
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
            self.dictionary_to_store_class_name = {
                'h1': r'^Constitution of the State|^CONSTITUTION OF THE UNITED STATES',
                'li': r'^Preamble', 'h2': '^Article I',
                'History': r'History of Section\.|Cross References\.', 'junk': '^Text$',
                'h3': r'^§ \d\.', 'ol_of_i': '^—', 'h4': r'Compiler’s Notes\.'}
            self.get_class_name()
            self.remove_junk()
            self.convert_to_header_and_assign_id_for_constitution()
            self.create_nav_and_ul_tag_for_constitution()
            self.create_nav_and_main_tag()
            self.create_ol_tag()
            self.add_citation()
            self.create_div_tag_for_constitution()
        else:
            self.get_class_name()
            self.remove_junk()
            self.convert_to_header_and_assign_id()
            self.create_nav_and_ul_tag()
            self.create_nav_and_main_tag()
            self.create_ol_tag()
            self.add_citation()
            self.create_div_tag()
        self.remove_from_header_tag()
        self.adding_css_to_file()
        self.add_watermark()
        self.cleanup()
        self.write_to_file()
        print(f'finished {self.html_file}')
        print(datetime.now() - start_time)
