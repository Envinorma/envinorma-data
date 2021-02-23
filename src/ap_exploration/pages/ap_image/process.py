import argparse
import json
import os
import pickle
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pdf2image
import pytesseract
from envinorma.io.alto import AltoFile, AltoPage
from envinorma.utils import write_json
from tqdm import tqdm


def _ensure_one_page_and_get_it(alto: AltoFile) -> AltoPage:
    if len(alto.layout.pages) != 1:
        raise ValueError(f'Expecting exactly one page, got {len(alto.layout.pages)}')
    return alto.layout.pages[0]


def _decode(content: Union[str, bytes]) -> str:
    return content.decode() if isinstance(content, bytes) else content


def _tesseract(page: Any) -> str:
    return _decode(pytesseract.image_to_alto_xml(page, lang='fra'))  # config='user_words_file words'


def _remove_pdf_extension(filename: str) -> str:
    if not filename.endswith('.pdf'):
        raise ValueError(f'Expecting pdf file, got {filename}')
    return filename[:-4]


def _ocr(filename: str):
    print('Converting to image.')
    pages = pdf2image.convert_from_path(filename)
    print('OCRing.')
    return [pytesseract.image_to_alto_xml(page, lang='fra') for page in tqdm(pages)]


def _nb_page_filename(filename: str) -> str:
    return os.path.join(_remove_pdf_extension(filename), 'nb_pages.json')


def _load_nb_page(filename: str) -> Optional[int]:
    nb_page_filename = _nb_page_filename(filename)
    if os.path.exists(nb_page_filename):
        with open(nb_page_filename) as file_:
            return json.load(file_)
    return None


def _raw_page_filename(filename: str, page_number: int) -> str:
    return os.path.join(_remove_pdf_extension(filename), f'page_{page_number}.raw')


def _alto_page_filename(filename: str, page_number: int) -> str:
    return os.path.join(_remove_pdf_extension(filename), f'page_{page_number}.alto')


def _create_if_inexistent(folder_name: str) -> None:
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)


def _dump_pages_and_nb_pages(filename: str) -> int:
    pages = pdf2image.convert_from_path(filename)
    _create_if_inexistent(_remove_pdf_extension(filename))
    for page_nb, page in enumerate(pages):
        path = _raw_page_filename(filename, page_nb)
        with open(path, 'wb') as file_:
            pickle.dump(page, file_)
    json.dump(len(pages), open(_nb_page_filename(filename), 'w'))
    return len(pages)


def _ocr_page(input_filename: str, output_filename: str) -> None:
    string_xml = _tesseract(_load_raw_page(input_filename))
    json.dump(string_xml, open(output_filename, 'w'))


def _load_raw_page(filename: str) -> Optional[Any]:
    with open(filename, 'rb') as file_:
        return pickle.load(file_)


def _final_alto_file(filename: str) -> str:
    return _remove_pdf_extension(filename) + '.alto'


def _generate_alto_file(nb_pages: int, filename: str) -> None:
    page_contents: List[str] = []
    for page_nb in range(nb_pages):
        with open(_alto_page_filename(filename, page_nb)) as file_:
            page_contents.append(json.load(file_))
    with open(_final_alto_file(filename), 'w') as file_:
        json.dump(page_contents, file_)


@dataclass
class OCRProcessingStep:
    messsage: Optional[str]
    advancement: float
    done: bool

    def __post_init__(self) -> None:
        assert 0 <= self.advancement <= 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'OCRProcessingStep':
        return cls(**dict_)


def _process_next_step(filename: str) -> OCRProcessingStep:
    nb_pages = _load_nb_page(filename)
    if nb_pages is None:
        nb_pages = _dump_pages_and_nb_pages(filename)
        return OCRProcessingStep(f'OCR on page 1/{nb_pages}', 0.1, False)
    for page_nb in range(nb_pages):
        alto_page_filename = _alto_page_filename(filename, page_nb)
        if os.path.exists(alto_page_filename):
            continue
        _ocr_page(_raw_page_filename(filename, page_nb), alto_page_filename)
        return OCRProcessingStep(f'OCR on page {page_nb + 2}/{nb_pages}', 0.1 + 0.9 * (page_nb + 1) / nb_pages, False)
    if not os.path.exists(_final_alto_file(filename)):
        _generate_alto_file(nb_pages, filename)
    return OCRProcessingStep(None, 1.0, True)


def _step_filename(filename: str) -> str:
    return os.path.join(_remove_pdf_extension(filename), 'step.json')


def _dump_step(filename: str, step: OCRProcessingStep) -> None:
    step_filename = _step_filename(filename)
    write_json(step.to_dict(), step_filename)


def load_step(filename: str) -> OCRProcessingStep:
    step_filename = _step_filename(filename)
    if not os.path.exists(step_filename):
        return OCRProcessingStep(None, 0, False)
    with open(step_filename) as file_:
        return OCRProcessingStep.from_dict(json.load(file_))


def _process_file(filename: str) -> None:
    step = OCRProcessingStep(None, 0, False)
    while not step.done:
        print(f'Advancement: {step.advancement*100}%')
        step = _process_next_step(filename)
        _dump_step(filename, step)


def extract_alto_pages(filename: str) -> List[AltoPage]:
    step = _process_next_step(filename)
    while not step.done:
        print(f'Advancement: {step.advancement*100}%')
        step = _process_next_step(filename)
    with open(_final_alto_file(filename)) as file_:
        pages = json.load(file_)
    return [_ensure_one_page_and_get_it(AltoFile.from_xml(page)) for page in pages]


def start_process(filename: str) -> None:
    cmd = ['python3', __file__, '--filename', filename]
    subprocess.Popen(cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--filename', required=True)
    args = parser.parse_args()
    _process_file(args.filename)
