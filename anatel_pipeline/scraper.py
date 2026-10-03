"""Extração: navega no portal Spectrum-E (Mosaico/Anatel) e baixa o ZIP de uma UF.

O portal não oferece a base nacional consolidada: exige aplicar o filtro de
estado em "Filtros Adicionais" antes de liberar o download. O Playwright
reproduz esse fluxo em modo headless.
"""
import logging
import time

URL = "https://sistemas.anatel.gov.br/se/public/view/b/licenciamento.php"
# Estados grandes (SP, MG) levam vários minutos para o portal compilar o arquivo
DOWNLOAD_TIMEOUT_MS = 10 * 60 * 1000

log = logging.getLogger(__name__)


def download_state_data(uf: str, zip_path: str) -> None:
    from playwright.sync_api import sync_playwright  # import tardio: os testes não precisam do navegador

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            log.info("[%s] Acessando %s", uf, URL)
            page.goto(URL, timeout=90_000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)  # componentes do filtro carregam depois do networkidle

            page.locator("#filtros_adicionais").wait_for(state="visible", timeout=30_000)
            page.locator("#filtros_adicionais").click()
            time.sleep(2)

            page.select_option("select#fa_gsearch", value="2")  # tipo de busca = Estado
            time.sleep(1)
            page.select_option("select#fa_uf", value=uf)
            time.sleep(1)
            page.locator("#import").click()
            time.sleep(5)  # aguarda a tabela atualizar com o filtro

            page.locator("#download_csv").wait_for(state="visible", timeout=30_000)
            log.info("[%s] Solicitando download (timeout de %d min)", uf, DOWNLOAD_TIMEOUT_MS // 60_000)
            with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as download_info:
                page.locator("#download_csv").click()

            download = download_info.value
            download.save_as(zip_path)
            log.info("[%s] ZIP salvo em %s", uf, zip_path)
        finally:
            browser.close()
