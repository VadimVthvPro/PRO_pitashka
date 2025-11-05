"""
Модуль управления путями к файлам проекта PROpitashka.
Обеспечивает кросс-платформенную совместимость.

Автор: PROpitashka Team
Дата: 2025-01-15
"""
import os
from pathlib import Path
from typing import Optional

# Корневая директория проекта (где находится main.py)
BASE_DIR = Path(__file__).resolve().parent

# Директории с ресурсами
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
GIFS_DIR = ASSETS_DIR / "gifs"
DOCS_DIR = ASSETS_DIR / "documents"

# Конкретные файлы
LOGO_PATH = IMAGES_DIR / "logo.jpg"
PRIVACY_POLICY_DIR = BASE_DIR

# Создание директорий при импорте модуля
for directory in [ASSETS_DIR, IMAGES_DIR, GIFS_DIR, DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def validate_assets() -> None:
    """
    Проверяет наличие критичных файлов при запуске.
    
    Raises:
        FileNotFoundError: Если критичные файлы отсутствуют
    """
    critical_files = [LOGO_PATH]
    missing = [f for f in critical_files if not f.exists()]
    
    if missing:
        raise FileNotFoundError(
            f"❌ Критичные файлы отсутствуют:\n" +
            "\n".join(f"  - {f}" for f in missing) +
            "\n\n💡 Убедитесь, что все файлы находятся в правильных директориях."
        )


def get_privacy_policy_path(lang_code: str) -> Path:
    """
    Возвращает путь к файлу политики конфиденциальности для заданного языка.
    
    Args:
        lang_code: Код языка (ru, en, de, fr, es)
        
    Returns:
        Path объект к файлу
        
    Raises:
        FileNotFoundError: Если файл не найден (включая fallback)
    """
    filename = f"privacy_policy_{lang_code}.txt"
    filepath = PRIVACY_POLICY_DIR / filename
    
    if not filepath.exists():
        # Fallback на английский
        filepath = PRIVACY_POLICY_DIR / "privacy_policy_en.txt"
        if not filepath.exists():
            raise FileNotFoundError(
                f"❌ Privacy policy file not found: {filename}\n"
                f"💡 Создайте файл {filename} в корневой директории проекта"
            )
    
    return filepath


def get_gif_path(gif_name: str) -> Optional[Path]:
    """
    Возвращает путь к GIF-файлу упражнения.
    
    Args:
        gif_name: Название файла (например, 'bench_press.gif')
        
    Returns:
        Path объект или None, если файл не найден
    """
    filepath = GIFS_DIR / gif_name
    return filepath if filepath.exists() else None


def get_asset_path(asset_name: str, asset_type: str = 'images') -> Optional[Path]:
    """
    Универсальная функция для получения пути к ресурсу.
    
    Args:
        asset_name: Название файла
        asset_type: Тип ресурса ('images', 'gifs', 'documents')
        
    Returns:
        Path объект или None, если файл не найден
    """
    asset_dirs = {
        'images': IMAGES_DIR,
        'gifs': GIFS_DIR,
        'documents': DOCS_DIR,
    }
    
    asset_dir = asset_dirs.get(asset_type)
    if not asset_dir:
        return None
    
    filepath = asset_dir / asset_name
    return filepath if filepath.exists() else None


def ensure_directory(directory_path: Path) -> None:
    """
    Гарантирует существование директории.
    
    Args:
        directory_path: Путь к директории
    """
    directory_path.mkdir(parents=True, exist_ok=True)


# Информация о путях для логирования
def print_paths_info():
    """Выводит информацию о путях для отладки."""
    print("=" * 70)
    print("📁 PROpitashka - Конфигурация путей")
    print("=" * 70)
    print(f"🏠 Корневая директория: {BASE_DIR}")
    print(f"📦 Assets: {ASSETS_DIR}")
    print(f"  ├─ 🖼️  Images: {IMAGES_DIR}")
    print(f"  ├─ 🎬 GIFs: {GIFS_DIR}")
    print(f"  └─ 📄 Documents: {DOCS_DIR}")
    print()
    print(f"🖼️  Логотип: {LOGO_PATH} {'✅' if LOGO_PATH.exists() else '❌ НЕ НАЙДЕН'}")
    print("=" * 70)


if __name__ == "__main__":
    # Тестирование модуля
    print_paths_info()
    
    try:
        validate_assets()
        print("\n✅ Все критичные файлы на месте!")
    except FileNotFoundError as e:
        print(f"\n{e}")


