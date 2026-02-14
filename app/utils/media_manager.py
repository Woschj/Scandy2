import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from app.utils.logger import loggers
from PIL import Image
import io

class MediaManager:
    """Universelles Medien-Management-System"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    MAX_IMAGES_PER_ENTITY = 10
    MAX_IMAGE_SIZE = (1920, 1080)  # 1080p
    
    @staticmethod
    def allowed_file(filename):
        """Prüft ob Dateityp erlaubt ist"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in MediaManager.ALLOWED_EXTENSIONS
    
    @staticmethod
    def get_upload_folder(entity_type, entity_id):
        """Erstellt und gibt Upload-Ordner zurück"""
        upload_path = os.path.join(current_app.root_path, 'static', 'uploads', entity_type, str(entity_id))
        
        loggers['user_actions'].info(f"Erstelle Ordner: {upload_path}")
        loggers['user_actions'].info(f"Root-Pfad: {current_app.root_path}")
        
        os.makedirs(upload_path, exist_ok=True)
        
        loggers['user_actions'].info(f"Ordner erstellt: {os.path.exists(upload_path)}")
        loggers['user_actions'].info(f"Ordner-Inhalt: {os.listdir(upload_path) if os.path.exists(upload_path) else 'N/A'}")
        
        return upload_path
    
    @staticmethod
    def get_media_folder_path(entity_type, entity_id):
        """Gibt relativen Pfad für Frontend zurück"""
        return f"uploads/{entity_type}/{entity_id}"
    
    @staticmethod
    def resize_image(image_path, max_size=MAX_IMAGE_SIZE):
        """Skaliert Bild auf maximale Größe mit verbesserter Verarbeitung"""
        try:
            # Prüfe ob es eine SVG-Datei ist
            if image_path.lower().endswith('.svg'):
                loggers['user_actions'].info(f"SVG-Datei übersprungen: {image_path}")
                return True  # SVG-Dateien werden nicht skaliert
            
            # Prüfe ob es eine PDF-Datei ist
            if image_path.lower().endswith('.pdf'):
                loggers['user_actions'].info(f"PDF-Datei übersprungen: {image_path}")
                return True  # PDF-Dateien werden nicht skaliert
            
            with Image.open(image_path) as img:
                original_width, original_height = img.size
                loggers['user_actions'].info(f"Verarbeite Bild: {original_width}x{original_height}")
                
                # Konvertiere zu RGB falls nötig (für JPEG-Kompatibilität)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Erstelle weißes Hintergrundbild für transparente Bilder
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Automatische Skalierung basierend auf verschiedenen Kriterien
                max_dimension = 1920  # Maximale Breite/Höhe
                max_file_size = 5 * 1024 * 1024  # 5MB maximale Dateigröße
                
                # Skaliere wenn Bild zu groß ist
                if original_width > max_dimension or original_height > max_dimension:
                    # Berechne neue Größe mit Seitenverhältnis
                    if original_width > original_height:
                        new_width = max_dimension
                        new_height = int(original_height * max_dimension / original_width)
                    else:
                        new_height = max_dimension
                        new_width = int(original_width * max_dimension / original_height)
                    
                    # Skaliere das Bild
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    loggers['user_actions'].info(f"Bild skaliert auf: {new_width}x{new_height}")
                
                # Speichere mit optimierter Qualität
                save_options = {
                    'quality': 85,  # Gute Qualität, aber kompakter
                    'optimize': True,
                    'progressive': True  # Progressive JPEG für bessere Web-Performance
                }
                
                # Speichere das Bild
                img.save(image_path, **save_options)
                
                # Prüfe finale Dateigröße
                final_size = os.path.getsize(image_path)
                loggers['user_actions'].info(f"Finale Dateigröße: {final_size} bytes ({final_size/1024/1024:.2f} MB)")
                
                # Falls Datei immer noch zu groß, komprimiere weiter
                if final_size > max_file_size:
                    loggers['user_actions'].info("Datei immer noch zu groß, komprimiere weiter...")
                    
                    # Reduziere Qualität schrittweise
                    for quality in [70, 60, 50, 40]:
                        img.save(image_path, quality=quality, optimize=True, progressive=True)
                        if os.path.getsize(image_path) <= max_file_size:
                            loggers['user_actions'].info(f"Datei auf {quality}% Qualität komprimiert")
                            break
                    
                    final_size = os.path.getsize(image_path)
                    loggers['user_actions'].info(f"Finale komprimierte Größe: {final_size} bytes ({final_size/1024/1024:.2f} MB)")
                
                loggers['user_actions'].info(f"Bild erfolgreich verarbeitet: {img.size[0]}x{img.size[1]}")
                return True
                
        except ImportError:
            loggers['errors'].error("PIL/Pillow nicht verfügbar - Bildverarbeitung übersprungen")
            return False
        except Exception as e:
            loggers['errors'].error(f"Fehler bei der Bildverarbeitung: [Interner Fehler]")
            import traceback
            loggers['errors'].error(f"Bildverarbeitung Traceback: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def upload_media(file, entity_type, entity_id):
        """Lädt Medien für eine Entität hoch"""
        try:
            # Validierung
            if not file or not MediaManager.allowed_file(file.filename):
                return None, "Ungültiges Dateiformat. Nur Bilder (jpg, png, gif, webp) erlaubt."
            
            # Aktuelle Anzahl prüfen
            current_count = MediaManager.get_media_count(entity_type, entity_id)
            if current_count >= MediaManager.MAX_IMAGES_PER_ENTITY:
                return None, f"Maximal {MediaManager.MAX_IMAGES_PER_ENTITY} Bilder erlaubt."
            
            # Sicheren Dateinamen erstellen
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            
            # Ordner erstellen und Datei speichern
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            file_path = os.path.join(upload_folder, unique_filename)
            
            loggers['user_actions'].info(f"Upload-Pfad: {file_path}")
            loggers['user_actions'].info(f"Ordner existiert: {os.path.exists(upload_folder)}")
            
            file.save(file_path)
            
            loggers['user_actions'].info(f"Datei gespeichert: {os.path.exists(file_path)}")
            loggers['user_actions'].info(f"Dateigröße: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'} bytes")
            
            # Bild skalieren
            if not MediaManager.resize_image(file_path):
                os.remove(file_path)
                return None, "Fehler beim Verarbeiten des Bildes."
            
            loggers['user_actions'].info(f"Medien hochgeladen: {entity_type}/{entity_id}/{unique_filename}")
            return unique_filename, None
            
        except Exception as e:
            loggers['errors'].error(f"Upload-Fehler: [Interner Fehler]")
            return None, f"Fehler beim Hochladen: [Interner Fehler]"
    
    @staticmethod
    def delete_media(filename, entity_type, entity_id):
        """Löscht eine Mediendatei"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            file_path = os.path.join(upload_folder, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                loggers['user_actions'].info(f"Medien gelöscht: {file_path}")
                return True
            else:
                loggers['warnings'].warning(f"Datei nicht gefunden: {file_path}")
                return False
                
        except Exception as e:
            loggers['errors'].error(f"Delete-Fehler: [Interner Fehler]")
            return False
    
    @staticmethod
    def delete_all_media(entity_type, entity_id):
        """Löscht alle Medien einer Entität"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            
            if os.path.exists(upload_folder):
                for filename in os.listdir(upload_folder):
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                
                # Ordner löschen
                os.rmdir(upload_folder)
                loggers['user_actions'].info(f"Alle Medien gelöscht: {entity_type}/{entity_id}")
                return True
            else:
                loggers['info'].info(f"Kein Medien-Ordner gefunden: {upload_folder}")
                return True
                
        except Exception as e:
            loggers['errors'].error(f"Delete-All-Fehler: [Interner Fehler]")
            return False
    
    @staticmethod
    def get_media_count(entity_type, entity_id):
        """Gibt Anzahl der Medien zurück"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            if os.path.exists(upload_folder):
                return len([f for f in os.listdir(upload_folder) 
                          if os.path.isfile(os.path.join(upload_folder, f))])
            return 0
        except Exception as e:
            loggers['errors'].error(f"Count-Fehler: [Interner Fehler]")
            return 0
    
    @staticmethod
    def get_media_list(entity_type, entity_id):
        """Gibt Liste aller Medien zurück"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            media_list = []
            
            loggers['user_actions'].info(f"Suche Medien in: {upload_folder}")
            loggers['user_actions'].info(f"Ordner existiert: {os.path.exists(upload_folder)}")
            
            if os.path.exists(upload_folder):
                all_files = os.listdir(upload_folder)
                loggers['user_actions'].info(f"Alle Dateien im Ordner: {all_files}")
                
                for filename in all_files:
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.isfile(file_path) and MediaManager.allowed_file(filename):
                        media_list.append(filename)
                        loggers['user_actions'].info(f"Medien-Datei gefunden: {filename}")
                    else:
                        loggers['user_actions'].info(f"Datei übersprungen: {filename} (ist_datei={os.path.isfile(file_path)}, erlaubt={MediaManager.allowed_file(filename)})")
            
            loggers['user_actions'].info(f"Medien-Liste: {media_list}")
            return sorted(media_list)
        except Exception as e:
            loggers['errors'].error(f"List-Fehler: [Interner Fehler]")
            return [] 