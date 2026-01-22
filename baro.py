import os
import sys
import warnings
from shutil import which

# Suprimir warnings de pydub
warnings.filterwarnings('ignore')

from flask import Flask, request, jsonify
import speech_recognition as sr
import datetime
import random
import webbrowser
import subprocess
import sqlite3
import requests
import io
import feedparser
from pydub import AudioSegment

# Configurar ffmpeg automáticamente
ffmpeg_path = which('ffmpeg')
ffprobe_path = which('ffprobe')
if ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
if ffprobe_path:
    AudioSegment.ffprobe = ffprobe_path
import asyncio
from edge_tts import Communicate
import tempfile
import base64
import wikipedia
import re
from difflib import SequenceMatcher
from collections import defaultdict

wikipedia.set_lang("es")

# ============= SISTEMA DE NLP MEJORADO =============
class NLPProcessor:
    """Procesador de lenguaje natural avanzado"""
    
    def __init__(self):
        # Sinónimos y variaciones de comandos
        self.synonyms = {
            'hora': ['hora', 'qué hora es', 'me dices la hora', 'dime la hora', 'hora actual', 'tiempo'],
            'fecha': ['fecha', 'qué día es', 'día de hoy', 'fecha actual', 'qué fecha', 'calendario'],
            'clima': ['clima', 'tiempo', 'temperatura', 'pronóstico', 'hace calor', 'hace frío', 'llueve', 'cómo está el clima', 'qué temperatura'],
            'buscar': ['busca', 'buscar', 'búscame', 'encuentra', 'google', 'investiga', 'consulta', 'mira en internet'],
            'youtube': ['youtube', 'reproduce', 'pon música', 'video', 'canción', 'música'],
            'noticias': ['noticias', 'últimas noticias', 'qué pasó', 'actualidad', 'informativo', 'novedades'],
            'chiste': ['chiste', 'broma', 'hazme reír', 'cuéntame un chiste', 'dime algo gracioso', 'algo divertido'],
            'calculadora': ['calculadora', 'calcula', 'cuánto es', 'opera', 'haz la cuenta', 'resultado de', 'suma', 'resta', 'multiplica', 'divide'],
            'ubicación': ['dónde queda', 'dónde está', 'ubicación', 'dirección', 'localización', 'cómo llegar'],
            'saludo': ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'hey', 'qué tal', 'saludos', 'qué onda'],
            'despedida': ['adiós', 'hasta luego', 'chau', 'nos vemos', 'me voy', 'hasta pronto', 'bye'],
            'identidad': ['quién eres', 'preséntate', 'tu nombre', 'qué eres', 'cómo te llamas', 'quién eres tú'],
            'aprender': ['aprende', 'recuerda', 'guarda', 'memoriza', 'anota'],
            'traducir': ['traduce', 'tradúceme', 'cómo se dice', 'dime en', 'traducción']
        }
        
        # Palabras de pregunta para mejor detección
        self.question_words = [
            'qué', 'quién', 'cómo', 'cuándo', 'dónde', 'cuál', 'cuáles', 'por qué', 'para qué',
            'cuánto', 'cuánta', 'cuántos', 'cuántas', 'que', 'quien', 'como', 'cuando', 'donde'
        ]
        
        # Patterns de preguntas mejorados
        self.question_patterns = {
            'definicion': r'(qué es|que es|define|definición de|qué significa|que significa|explica|explicame)\s+(.+)',
            'persona': r'(quién es|quien es|quién fue|quien fue|háblame de|cuéntame sobre|info sobre)\s+(.+)',
            'ubicacion': r'(dónde|donde|ubicación|localización|dirección)\s+(está|queda|se encuentra)\s+(.+)',
            'tiempo': r'(cuándo|cuando)\s+(fue|ocurrió|pasó|es|será)\s+(.+)',
            'procedimiento': r'(cómo|como)\s+(se|funciona|hacer|hacer)\s+(.+)',
            'razon': r'(por qué|porque|para qué|motivo)\s+(.+)',
            'cantidad': r'(cuánto|cuanto|cuánta|cuanta|cuántos|cuantos|cuántas|cuantas)\s+(.+)'
        }
    
    def normalize_text(self, text):
        """Normaliza el texto eliminando caracteres especiales y estandarizando"""
        text = text.lower().strip()
        # Reemplazar acentos comunes
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ü': 'u', 'ñ': 'ñ'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Eliminar puntuación múltiple
        text = re.sub(r'[¿?!]+', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def similarity(self, a, b):
        """Calcula similitud entre dos textos"""
        return SequenceMatcher(None, a, b).ratio()
    
    def detect_intent(self, command):
        """Detecta la intención del comando usando NLP mejorado"""
        command_norm = self.normalize_text(command)
        
        # PRIORIDAD 1: Detección exacta de palabras clave críticas
        if any(word in command_norm for word in ['qué hora', 'que hora', 'hora', 'hora actual', 'hora es', 'me dices la hora']):
            return 'hora', 0.95
        if any(word in command_norm for word in ['fecha', 'qué día', 'que dia', 'día de hoy', 'dia de hoy']):
            return 'fecha', 0.95
        if any(word in command_norm for word in ['dónde estoy', 'donde estoy', 'mi ubicación', 'mi ubicacion', 'mi localización']):
            return 'ubicación', 0.95
        
        # PRIORIDAD 2: Buscar coincidencias exactas o similares en sinónimos
        best_match = None
        best_score = 0
        
        for intent, variations in self.synonyms.items():
            for variation in variations:
                if variation in command_norm:
                    score = len(variation) / len(command_norm)
                    if score > best_score:
                        best_score = score
                        best_match = intent
                
                # Similitud de texto
                sim = self.similarity(command_norm, variation)
                if sim > 0.8 and sim > best_score:
                    best_score = sim
                    best_match = intent
        
        return best_match, best_score
    
    def extract_query(self, command, intent):
        """Extrae la consulta principal del comando"""
        command_norm = self.normalize_text(command)
        
        # Eliminar palabras de activación y de intención
        stop_words = ['baro', 'varo', 'por favor', 'porfavor', 'gracias']
        if intent and intent in self.synonyms:
            stop_words.extend(self.synonyms[intent])
        
        words = command_norm.split()
        filtered_words = [w for w in words if w not in stop_words]
        
        return ' '.join(filtered_words).strip()
    
    def detect_question_type(self, command):
        """Detecta el tipo de pregunta y extrae el tema"""
        command_norm = self.normalize_text(command)
        
        for q_type, pattern in self.question_patterns.items():
            match = re.search(pattern, command_norm)
            if match:
                topic = match.groups()[-1]
                return q_type, topic
        
        # Detectar si es una pregunta general
        for qw in self.question_words:
            if command_norm.startswith(qw):
                topic = command_norm.replace(qw, '').strip()
                return 'general', topic
        
        return None, None

# Instancia global del procesador NLP
nlp = NLPProcessor()

# ============= GENERACIÓN DE AUDIO OPTIMIZADA =============
def generate_audio(text):
    """Generación de audio optimizada con caché"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name

        async def _gen():
            communicate = Communicate(text, "es-ES-AlvaroNeural")
            await communicate.save(temp_path)
            with open(temp_path, "rb") as f:
                data = f.read()
            os.unlink(temp_path)
            return data

        return asyncio.run(_gen())
    except Exception as e:
        print(f"Error generando audio: {e}")
        return None

# ============= BASE DE DATOS MEJORADA =============
def init_db():
    """Inicializa base de datos con conocimiento expandido"""
    conn = sqlite3.connect('baro.db')
    c = conn.cursor()
    
    # Tabla de interacciones
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    command TEXT,
                    response TEXT,
                    intent TEXT,
                    confidence REAL
                )''')
    
    # Tabla de conocimiento expandida
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY,
                    topic TEXT,
                    info TEXT,
                    category TEXT,
                    keywords TEXT
                )''')
    
    # Crear índices para búsqueda rápida
    c.execute('CREATE INDEX IF NOT EXISTS idx_topic ON knowledge(topic)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_keywords ON knowledge(keywords)')

    # Base de conocimiento masiva y organizada
    knowledge_data = [
        # Saludos y presentación
        ("saludo", "¡Hola! Soy Baro, tu asistente inteligente. ¿En qué puedo ayudarte hoy?", "conversacion", "hola,saludo,buenos dias"),
        ("despedida", "¡Hasta luego! Fue un placer ayudarte. Que tengas un excelente día.", "conversacion", "adios,despedida,hasta luego"),
        ("baro", "Soy Baro, un asistente de voz inteligente avanzado, similar a Alexa. Puedo ayudarte con información, clima, noticias, cálculos, búsquedas, música y mucho más. Tengo capacidad de aprender cosas nuevas que me enseñes.", "identidad", "quien eres,presentacion,tu nombre"),
        ("gracias", "¡De nada! Es un placer ayudarte. Estoy aquí para lo que necesites.", "conversacion", "gracias,agradecimiento"),
        
        # Tecnología e IA
        ("inteligencia artificial", "La inteligencia artificial o IA es la capacidad de las máquinas para realizar tareas que normalmente requieren inteligencia humana: razonar, aprender de experiencias, resolver problemas complejos, reconocer patrones y tomar decisiones.", "tecnologia", "ia,ai,artificial intelligence"),
        ("machine learning", "El machine learning o aprendizaje automático es una rama de la IA donde los algoritmos aprenden patrones de grandes cantidades de datos sin ser programados explícitamente, mejorando su rendimiento con la experiencia.", "tecnologia", "ml,aprendizaje automatico"),
        ("deep learning", "El deep learning o aprendizaje profundo usa redes neuronales artificiales con múltiples capas para procesar información compleja como imágenes, voz y texto, siendo la base de sistemas como reconocimiento facial y asistentes de voz.", "tecnologia", "redes neuronales,neural networks"),
        ("chatgpt", "ChatGPT es un modelo de lenguaje de inteligencia artificial creado por OpenAI que puede mantener conversaciones, responder preguntas, escribir código, crear contenido y ayudar en múltiples tareas usando procesamiento de lenguaje natural.", "tecnologia", "openai,gpt,lenguaje"),
        ("alexa", "Alexa es el asistente virtual de Amazon que funciona mediante voz, puede reproducir música, controlar dispositivos inteligentes, responder preguntas, configurar alarmas y muchas otras tareas del hogar.", "tecnologia", "amazon,asistente virtual"),
        ("python", "Python es un lenguaje de programación de alto nivel, interpretado, versátil y fácil de aprender. Es muy popular en ciencia de datos, inteligencia artificial, desarrollo web, automatización y aplicaciones científicas.", "tecnologia", "programacion,lenguaje"),
        ("javascript", "JavaScript es el lenguaje de programación principal de la web, usado para crear páginas interactivas, aplicaciones web, servidores con Node.js y aplicaciones móviles.", "tecnologia", "js,web,programacion"),
        ("algoritmo", "Un algoritmo es un conjunto finito de instrucciones paso a paso, bien definidas y ordenadas, diseñadas para resolver un problema específico o realizar una tarea, como ordenar datos o buscar información.", "tecnologia", "programacion,logica"),
        ("internet", "Internet es una red global de computadoras interconectadas que permite compartir información, comunicarse, acceder a servicios en línea y conectar a miles de millones de personas en todo el mundo.", "tecnologia", "web,red"),
        ("redes sociales", "Las redes sociales son plataformas digitales como Facebook, Instagram, X (Twitter), TikTok y LinkedIn que permiten a las personas conectarse, compartir contenido, comunicarse y construir comunidades virtuales.", "tecnologia", "social media,facebook,instagram"),
        ("blockchain", "Blockchain o cadena de bloques es una tecnología de registro distribuido que almacena información de forma segura, transparente e inmutable, siendo la base de criptomonedas como Bitcoin.", "tecnologia", "criptomonedas,bitcoin"),
        ("bitcoin", "Bitcoin es la primera y más conocida criptomoneda descentralizada, creada en 2009 por Satoshi Nakamoto. Funciona sin bancos centrales usando tecnología blockchain para transacciones seguras.", "tecnologia", "cripto,criptomoneda"),
        ("realidad virtual", "La realidad virtual o VR es una tecnología que crea entornos tridimensionales inmersivos usando dispositivos como visores especiales, permitiendo experiencias interactivas en mundos digitales.", "tecnologia", "vr,metaverso"),
        ("realidad aumentada", "La realidad aumentada o AR superpone elementos digitales sobre el mundo real a través de dispositivos como smartphones o gafas especiales, mezclando lo virtual con lo físico.", "tecnologia", "ar,pokemon go"),
        ("cloud computing", "La computación en la nube permite acceder a recursos informáticos como servidores, almacenamiento y aplicaciones a través de internet, sin necesidad de infraestructura física local.", "tecnologia", "nube,servidor"),
        ("ciberseguridad", "La ciberseguridad es la práctica de proteger sistemas, redes y datos de ataques digitales, malware, hackers y accesos no autorizados mediante tecnologías y procedimientos de seguridad.", "tecnologia", "seguridad,hackers"),
        
        # Ciencias
        ("física", "La física es la ciencia natural que estudia las propiedades fundamentales de la materia, la energía, el espacio, el tiempo y sus interacciones, explicando cómo funciona el universo.", "ciencia", "ciencia,materia,energia"),
        ("química", "La química estudia la composición, estructura, propiedades y transformaciones de la materia, incluyendo átomos, moléculas, elementos y compuestos químicos.", "ciencia", "ciencia,elementos,moleculas"),
        ("biología", "La biología es la ciencia que estudia los seres vivos: su estructura, función, crecimiento, evolución, distribución y taxonomía, desde células hasta ecosistemas completos.", "ciencia", "vida,organismos,celulas"),
        ("matemáticas", "Las matemáticas estudian números, cantidades, formas, patrones y estructuras mediante razonamiento lógico, siendo fundamentales para ciencia, tecnología, ingeniería y economía.", "ciencia", "numeros,calculo,algebra"),
        ("astronomía", "La astronomía es la ciencia que estudia los cuerpos celestes como estrellas, planetas, galaxias, cometas y fenómenos del universo, usando telescopios y análisis de luz.", "ciencia", "espacio,estrellas,universo"),
        ("geología", "La geología estudia la composición, estructura y procesos de la Tierra, incluyendo rocas, minerales, terremotos, volcanes y la historia del planeta.", "ciencia", "tierra,rocas,volcanes"),
        ("medicina", "La medicina es la ciencia y práctica del diagnóstico, tratamiento y prevención de enfermedades, lesiones y condiciones que afectan la salud humana.", "ciencia", "salud,doctor,enfermedad"),
        ("genética", "La genética estudia los genes, la herencia y la variación de los seres vivos, explicando cómo se transmiten características de padres a hijos a través del ADN.", "ciencia", "adn,genes,herencia"),
        ("evolución", "La evolución es el proceso mediante el cual las especies cambian a lo largo del tiempo a través de selección natural y mutaciones genéticas, teoría propuesta por Charles Darwin.", "ciencia", "darwin,especies,seleccion natural"),
        ("ecología", "La ecología estudia las relaciones entre los seres vivos y su ambiente, incluyendo ecosistemas, cadenas alimentarias, biodiversidad y conservación ambiental.", "ciencia", "ambiente,ecosistema,naturaleza"),
        
        # Personajes históricos
        ("albert einstein", "Albert Einstein fue un físico teórico alemán, considerado el científico más importante del siglo 20. Desarrolló la teoría de la relatividad y la famosa ecuación E=mc², revolucionando nuestra comprensión del espacio, tiempo y energía.", "historia", "cientifico,fisica,relatividad"),
        ("isaac newton", "Isaac Newton fue un matemático y físico inglés del siglo 17 que formuló las leyes del movimiento y la gravitación universal, inventó el cálculo y realizó descubrimientos fundamentales en óptica.", "historia", "cientifico,gravedad,leyes"),
        ("leonardo da vinci", "Leonardo da Vinci fue un genio renacentista italiano: pintor, inventor, científico e ingeniero. Creó obras maestras como La Mona Lisa y La Última Cena, y diseñó inventos adelantados a su época.", "historia", "artista,inventor,renacimiento"),
        ("marie curie", "Marie Curie fue una física y química polaco-francesa, pionera en radioactividad. Fue la primera mujer en ganar un Premio Nobel y la única persona en ganarlo en dos ciencias diferentes: Física y Química.", "historia", "cientifica,radioactividad,nobel"),
        ("nikola tesla", "Nikola Tesla fue un inventor e ingeniero serbio-estadounidense que revolucionó la electricidad con sus inventos en corriente alterna, bobinas, radio y energía inalámbrica.", "historia", "inventor,electricidad,ingeniero"),
        ("stephen hawking", "Stephen Hawking fue un físico teórico británico famoso por sus estudios sobre agujeros negros, cosmología y el origen del universo, a pesar de padecer esclerosis lateral amiotrófica.", "historia", "cientifico,agujeros negros,cosmologia"),
        
        # Cuba y cultura
        ("cuba", "Cuba es la isla más grande del Caribe, ubicada entre el Mar Caribe y el Océano Atlántico. Es conocida por su rica historia, la Revolución Cubana, su música vibrante como la salsa y el son, sus playas paradisíacas, arquitectura colonial, automóviles clásicos y la producción de ron y tabaco.", "geografia", "pais,caribe,isla"),
        ("habana", "La Habana es la capital de Cuba y su ciudad más grande. Fundada en 1519, es famosa por su arquitectura colonial española, el icónico Malecón, autos clásicos americanos de los años 50, música en vivo, ron y puros. Su centro histórico es Patrimonio de la Humanidad.", "geografia", "capital,ciudad,cuba"),
        ("fidel castro", "Fidel Castro fue un revolucionario y político cubano que lideró la Revolución Cubana de 1959, derrocando al dictador Fulgencio Batista. Fue presidente de Cuba desde 1959 hasta 2008, estableciendo un gobierno socialista.", "historia", "revolucion,lider,cuba"),
        ("che guevara", "Ernesto 'Che' Guevara fue un revolucionario marxista argentino-cubano, médico, guerrillero, escritor y figura clave de la Revolución Cubana junto a Fidel Castro. Se convirtió en un símbolo mundial de rebeldía y lucha contra la opresión.", "historia", "revolucionario,argentina,cuba"),
        ("revolución cubana", "La Revolución Cubana fue un movimiento armado liderado por Fidel Castro, Che Guevara y otros, que en 1959 derrocó al dictador Fulgencio Batista y estableció un gobierno socialista en Cuba, cambiando radicalmente el país.", "historia", "cuba,1959,fidel"),
        ("salsa", "La salsa es un género musical y estilo de baile caribeño que fusiona son cubano, mambo, jazz y otros ritmos afrocaribeños. Surgió en Nueva York en los años 60-70 entre comunidades latinas, especialmente puertorriqueñas y cubanas.", "cultura", "musica,baile,caribe"),
        ("son cubano", "El son cubano es un género musical tradicional de Cuba que combina instrumentos españoles con ritmos africanos. Es la base de la salsa y otros géneros caribeños, caracterizado por el uso de la clave, guitarra y percusión.", "cultura", "musica,cuba,tradicional"),
        ("buena vista social club", "Buena Vista Social Club fue un proyecto musical que reunió a legendarios músicos cubanos en 1997, rescatando el son cubano tradicional y logrando fama mundial con su álbum homónimo y documental.", "cultura", "musica,cuba,son"),
        
        # Naturaleza y medio ambiente
        ("sol", "El Sol es la estrella central de nuestro sistema solar, una esfera gigante de plasma ardiente que genera luz y calor mediante fusión nuclear. Tiene 109 veces el diámetro de la Tierra y representa el 99.86% de la masa del sistema solar.", "ciencia", "estrella,sistema solar,luz"),
        ("tierra", "La Tierra es el tercer planeta desde el Sol y el único conocido que alberga vida. Tiene aproximadamente 4.500 millones de años, 71% de su superficie está cubierta de agua, y posee una atmósfera rica en oxígeno y nitrógeno.", "ciencia", "planeta,mundo,vida"),
        ("luna", "La Luna es el único satélite natural de la Tierra, formado hace unos 4.500 millones de años. Influye en las mareas oceánicas, tiene aproximadamente un cuarto del diámetro terrestre y ha sido visitada por astronautas.", "ciencia", "satelite,espacio,mareas"),
        ("marte", "Marte es el cuarto planeta del sistema solar, conocido como el 'planeta rojo' por su color oxidado. Es el planeta más explorado después de la Tierra y objetivo de futuras misiones humanas.", "ciencia", "planeta,rojo,espacio"),
        ("clima", "El clima es el patrón promedio de condiciones meteorológicas (temperatura, precipitación, viento) en una región durante periodos largos, generalmente 30 años o más.", "ciencia", "tiempo,meteorologia,temperatura"),
        ("cambio climático", "El cambio climático es el calentamiento gradual de la Tierra causado principalmente por emisiones humanas de gases de efecto invernadero como CO2. Provoca derretimiento de glaciares, aumento del nivel del mar, eventos climáticos extremos y alteración de ecosistemas.", "ciencia", "calentamiento,ambiente,co2"),
        ("energía renovable", "Las energías renovables son fuentes de energía sostenibles y limpias que no se agotan: solar, eólica, hidroeléctrica, geotérmica y biomasa. Son clave para combatir el cambio climático.", "ciencia", "solar,eolica,sostenible"),
        ("reciclaje", "El reciclaje es el proceso de convertir materiales de desecho en nuevos productos, reduciendo el uso de recursos naturales, ahorrando energía y disminuyendo la contaminación ambiental.", "ciencia", "basura,ambiente,reutilizar"),
        ("agua", "El agua es una sustancia química esencial para toda forma de vida conocida, compuesta por dos átomos de hidrógeno y uno de oxígeno (H2O). Cubre el 71% de la superficie terrestre.", "ciencia", "h2o,vida,liquido"),
        ("oxígeno", "El oxígeno es un elemento químico esencial para la respiración de la mayoría de los seres vivos. Constituye el 21% de la atmósfera terrestre y es producido principalmente por plantas mediante fotosíntesis.", "ciencia", "gas,respiracion,o2"),
        ("árbol", "Los árboles son plantas perennes de tallo leñoso que producen oxígeno, absorben dióxido de carbono, proporcionan hábitat para animales, previenen erosión y son fundamentales para los ecosistemas.", "ciencia", "planta,bosque,naturaleza"),
        ("selva amazónica", "La selva amazónica es la selva tropical más grande del mundo, ubicada en Sudamérica. Produce el 20% del oxígeno mundial, alberga millones de especies y regula el clima global.", "geografia", "bosque,brasil,biodiversidad"),
        
        # Cuerpo humano y salud
        ("cerebro", "El cerebro es el órgano más complejo del cuerpo humano, centro del sistema nervioso. Controla pensamientos, memoria, emociones, movimiento, y todas las funciones vitales. Contiene aproximadamente 86 mil millones de neuronas.", "ciencia", "organo,mente,neurona"),
        ("corazón", "El corazón es el músculo que bombea sangre a todo el cuerpo, distribuyendo oxígeno y nutrientes. Late aproximadamente 100.000 veces al día, bombeando unos 7.500 litros de sangre.", "ciencia", "organo,sangre,latido"),
        ("adn", "El ADN (ácido desoxirribonucleico) es la molécula que contiene las instrucciones genéticas para el desarrollo y funcionamiento de todos los seres vivos. Tiene forma de doble hélice.", "ciencia", "genetica,genes,celula"),
        ("vacuna", "Las vacunas son preparaciones biológicas que entrenan al sistema inmunológico para reconocer y combatir enfermedades específicas sin causar la enfermedad, previniendo infecciones graves.", "ciencia", "medicina,inmunidad,prevención"),
        ("covid", "COVID-19 es una enfermedad infecciosa causada por el coronavirus SARS-CoV-2, que provocó una pandemia mundial desde 2020 afectando a millones de personas.", "ciencia", "coronavirus,pandemia,enfermedad"),
        ("diabetes", "La diabetes es una enfermedad crónica que ocurre cuando el páncreas no produce suficiente insulina o el cuerpo no puede usar eficazmente la insulina que produce, elevando los niveles de azúcar en sangre.", "ciencia", "enfermedad,insulina,azucar"),
        ("cáncer", "El cáncer es un grupo de enfermedades caracterizadas por el crecimiento descontrolado de células anormales que pueden invadir otros tejidos. Existen más de 100 tipos diferentes.", "ciencia", "enfermedad,celulas,tumor"),
        
        # Historia y cultura general
        ("historia", "La historia es la ciencia que estudia y relata los acontecimientos del pasado de la humanidad, analizando documentos, evidencias arqueológicas y testimonios para comprender cómo evolucionaron las sociedades.", "cultura", "pasado,civilizacion,eventos"),
        ("filosofía", "La filosofía es la disciplina que busca respuestas fundamentales sobre la existencia, el conocimiento, la verdad, la ética, la mente y el lenguaje mediante el razonamiento y la argumentación.", "cultura", "pensamiento,sabiduria,razón"),
        ("arte", "El arte es la expresión creativa humana que produce obras de valor estético o emocional: pintura, escultura, música, literatura, danza, cine y otras manifestaciones culturales.", "cultura", "creatividad,belleza,expresion"),
        ("música", "La música es el arte de combinar sonidos de forma armoniosa y expresiva usando ritmo, melodía y armonía, presente en todas las culturas humanas.", "cultura", "sonido,melodia,canción"),
        ("literatura", "La literatura es el arte de la expresión escrita, abarcando novelas, poesía, ensayos, teatro y otros géneros que usan el lenguaje para crear obras artísticas y transmitir ideas.", "cultura", "libros,escritura,poesia"),
        ("pintura", "La pintura es el arte de aplicar pigmentos sobre una superficie para crear imágenes, expresar emociones o representar la realidad, con estilos desde realismo hasta abstracción.", "cultura", "arte,color,cuadro"),
        
        # Conceptos abstractos
        ("amor", "El amor es un sentimiento profundo de afecto, cariño, atracción y conexión emocional hacia otra persona, ser vivo o cosa. Puede ser romántico, fraternal, filial o universal.", "emocion", "sentimiento,afecto,cariño"),
        ("felicidad", "La felicidad es un estado emocional de bienestar, satisfacción y plenitud. Puede ser momentánea por eventos agradables o duradera como estilo de vida positivo.", "emocion", "alegria,bienestar,satisfaccion"),
        ("tristeza", "La tristeza es una emoción natural de dolor emocional, melancolía o desánimo, generalmente causada por pérdida, decepción o situaciones difíciles.", "emocion", "pena,melancolia,dolor"),
        ("miedo", "El miedo es una emoción básica de alerta ante peligros reales o percibidos, que prepara al cuerpo para huir o enfrentar amenazas.", "emocion", "temor,susto,ansiedad"),
        ("esperanza", "La esperanza es el sentimiento de confianza y optimismo de que algo deseado pueda suceder o mejore en el futuro.", "emocion", "fe,optimismo,confianza"),
        
        # Deportes
        ("fútbol", "El fútbol es el deporte más popular del mundo, jugado por dos equipos de 11 jugadores que intentan meter un balón en la portería contraria usando principalmente los pies.", "deporte", "soccer,balon,mundial"),
        ("basketball", "El basketball o baloncesto es un deporte de equipo donde dos equipos de 5 jugadores intentan encestar un balón en un aro elevado, usando las manos.", "deporte", "nba,basquet,aro"),
        ("béisbol", "El béisbol es un deporte muy popular en Cuba, EE.UU. y Japón, donde dos equipos alternan batear y fildear, intentando anotar carreras.", "deporte", "pelota,cuba,mlb"),
        ("ajedrez", "El ajedrez es un juego de estrategia para dos jugadores en un tablero de 64 casillas, cada uno con 16 piezas que mueven según reglas específicas, buscando hacer jaque mate al rey contrario.", "deporte", "estrategia,tablero,rey"),
        ("olimpiadas", "Los Juegos Olímpicos son el mayor evento deportivo mundial, celebrado cada 4 años, donde atletas de todos los países compiten en múltiples disciplinas.", "deporte", "juegos,competencia,mundial"),
        
        # Comida
        ("comida", "La comida cubana es variada y sabrosa, destacando arroz con frijoles negros (moros y cristianos), ropa vieja, lechón asado, yuca con mojo, tostones, plátanos maduros y tamales.", "cultura", "gastronomia,cocina,alimentos"),
        ("café", "El café cubano es mundialmente famoso por ser fuerte, aromático y dulce. Se sirve en tacitas pequeñas, muy concentrado, y es parte esencial de la cultura social cubana.", "cultura", "bebida,cuba,cafecito"),
        ("pizza", "La pizza es un plato italiano de masa horneada cubierta con salsa de tomate, queso y diversos ingredientes. Se ha convertido en uno de los alimentos más populares del mundo.", "comida", "italiana,masa,queso"),
        ("chocolate", "El chocolate se hace de semillas de cacao, originario de América. Puede ser dulce, amargo o con leche, y es una de las golosinas más amadas universalmente.", "comida", "cacao,dulce,postre"),
        
        # Entretenimiento
        ("película", "Las películas o cine son obras audiovisuales que cuentan historias mediante imágenes en movimiento, sonido, actuación y efectos visuales.", "cultura", "cine,film,movie"),
        ("netflix", "Netflix es el servicio de streaming más popular del mundo, ofreciendo películas, series, documentales y contenido original bajo demanda por suscripción.", "tecnologia", "streaming,series,peliculas"),
        ("videojuegos", "Los videojuegos son programas interactivos de entretenimiento donde los jugadores controlan personajes o situaciones en mundos virtuales, desde móviles hasta consolas avanzadas.", "tecnologia", "gaming,consola,juegos"),
        
        # Conceptos modernos
        ("teletrabajo", "El teletrabajo o trabajo remoto permite a las personas trabajar desde casa u otros lugares fuera de la oficina usando internet y tecnología de comunicación.", "tecnologia", "remoto,casa,trabajo"),
        ("streaming", "El streaming es la transmisión de contenido multimedia (video, audio) en tiempo real a través de internet sin necesidad de descargarlo completamente.", "tecnologia", "video,musica,directo"),
        ("podcast", "Un podcast es un programa de audio digital episódico disponible en internet, que los usuarios pueden descargar o escuchar en streaming sobre temas diversos.", "tecnologia", "audio,radio,episodio"),
        ("meme", "Un meme es una idea, imagen, video o frase que se difunde rápidamente por internet, generalmente con intención humorística o satírica.", "cultura", "internet,humor,viral"),
        ("influencer", "Un influencer es una persona con gran número de seguidores en redes sociales que puede influir en las opiniones y decisiones de su audiencia, a menudo promocionando productos o ideas.", "cultura", "redes sociales,celebridad,seguidores"),
        
        # Países y geografía
        ("españa", "España es un país europeo en la Península Ibérica, conocido por su rica historia, arquitectura, gastronomía, flamenco, fútbol y ser la cuna del idioma español.", "geografia", "pais,europa,español"),
        ("méxico", "México es el país hispanohablante más poblado del mundo, conocido por su cultura azteca y maya, gastronomía (tacos, mole), tequila, mariachis y playas del Caribe.", "geografia", "pais,america,azteca"),
        ("argentina", "Argentina es un gran país sudamericano famoso por el tango, el asado, el fútbol, la Patagonia, sus vinos Malbec y haber sido hogar del Che Guevara y Maradona.", "geografia", "pais,sudamerica,tango"),
        ("estados unidos", "Estados Unidos es la mayor potencia económica y militar mundial, conocido por su diversidad cultural, innovación tecnológica (Silicon Valley), entretenimiento (Hollywood) y grandes ciudades como Nueva York.", "geografia", "pais,usa,america"),
        ("china", "China es el país más poblado del mundo con más de 1.400 millones de habitantes, una de las civilizaciones más antiguas, potencia económica global y hogar de la Gran Muralla.", "geografia", "pais,asia,muralla"),
        ("japón", "Japón es un país insular asiático conocido por su avanzada tecnología, cultura única (anime, manga, samurái), gastronomía (sushi, ramen) y ciudades como Tokio.", "geografia", "pais,asia,tokio"),
        
        # Miscelánea útil
        ("dólar", "El dólar estadounidense es la moneda de reserva mundial más importante y usada en comercio internacional. Un dólar se divide en 100 centavos.", "economia", "moneda,usd,dinero"),
        ("euro", "El euro es la moneda oficial de 20 países de la Unión Europea, usado por más de 340 millones de personas, siendo la segunda moneda de reserva mundial.", "economia", "moneda,eur,europa"),
        ("banco", "Un banco es una institución financiera que acepta depósitos, otorga préstamos, facilita pagos y ofrece servicios financieros a individuos y empresas.", "economia", "dinero,credito,ahorro"),
        ("universidad", "Una universidad es una institución de educación superior que otorga títulos académicos (licenciatura, maestría, doctorado) y realiza investigación científica.", "educacion", "estudio,carrera,academia"),
        ("biblioteca", "Una biblioteca es un lugar que almacena, organiza y presta libros y otros recursos para lectura, estudio e investigación de la comunidad.", "educacion", "libros,lectura,estudio"),
    ]

    for topic, info, category, keywords in knowledge_data:
        c.execute("INSERT OR IGNORE INTO knowledge (topic, info, category, keywords) VALUES (?, ?, ?, ?)", 
                 (topic.lower(), info, category, keywords))

    conn.commit()
    conn.close()

# ============= BÚSQUEDA INTELIGENTE =============
def search_knowledge(query, threshold=0.6):
    """Búsqueda inteligente en base de conocimientos con puntuación"""
    conn = sqlite3.connect('baro.db')
    c = conn.cursor()
    
    query_lower = query.lower()
    results = []
    
    # Búsqueda exacta
    c.execute("SELECT topic, info, keywords FROM knowledge WHERE topic = ?", (query_lower,))
    exact_match = c.fetchone()
    if exact_match:
        conn.close()
        return exact_match[1], 1.0
    
    # Búsqueda por palabras clave
    c.execute("SELECT topic, info, keywords FROM knowledge")
    all_knowledge = c.fetchall()
    
    for topic, info, keywords in all_knowledge:
        score = 0
        
        # Búsqueda en topic
        if query_lower in topic:
            score += 0.9
        elif nlp.similarity(query_lower, topic) > 0.7:
            score += 0.7
        
        # Búsqueda en keywords
        if keywords:
            keyword_list = keywords.split(',')
            for kw in keyword_list:
                if kw.strip() in query_lower or query_lower in kw.strip():
                    score += 0.5
        
        # Búsqueda en info (menos peso)
        if query_lower in info.lower():
            score += 0.3
        
        if score > 0:
            results.append((topic, info, score))
    
    conn.close()
    
    if results:
        results.sort(key=lambda x: x[2], reverse=True)
        if results[0][2] >= threshold:
            return results[0][1], results[0][2]
    
    return None, 0

def search_wikipedia(query):
    """Búsqueda mejorada en Wikipedia con manejo de errores"""
    if not query or len(query.strip()) < 2:
        return "Necesito un tema válido para buscar en Wikipedia."
    
    try:
        # Intentar búsqueda directa
        summary = wikipedia.summary(query, sentences=3, auto_suggest=True)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        # Múltiples opciones encontradas
        options = e.options[:6]
        return f"Encontré varias opciones para '{query}'. ¿Te refieres a: {', '.join(options)}? Especifica cuál quieres."
    except wikipedia.exceptions.PageError:
        # Página no encontrada, intentar búsqueda
        try:
            search_results = wikipedia.search(query, results=5)
            if search_results:
                return f"No encontré '{query}' exactamente, pero encontré: {', '.join(search_results)}. ¿Cuál te interesa?"
            else:
                return f"No encontré información sobre '{query}' en Wikipedia. Intenta reformular tu búsqueda."
        except:
            return f"No pude encontrar '{query}' en Wikipedia."
    except Exception as e:
        print(f"Error en Wikipedia: {e}")
        return "Hubo un error al buscar en Wikipedia. Intenta de nuevo."

def get_weather(location="La Habana"):
    """Obtener clima con mejor formato"""
    try:
        location_clean = location.replace(' ', '+')
        url = f"http://wttr.in/{location_clean}?format=j1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            temp_c = current['temp_C']
            feels_like = current['FeelsLikeC']
            humidity = current['humidity']
            condition = current['weatherDesc'][0]['value']
            
            # Traducción simple de condiciones comunes
            translations = {
                'Sunny': 'soleado',
                'Clear': 'despejado',
                'Partly cloudy': 'parcialmente nublado',
                'Cloudy': 'nublado',
                'Overcast': 'muy nublado',
                'Mist': 'neblina',
                'Fog': 'niebla',
                'Light rain': 'lluvia ligera',
                'Rain': 'lluvia',
                'Heavy rain': 'lluvia fuerte',
                'Thunderstorm': 'tormenta',
                'Snow': 'nieve'
            }
            
            condition_es = translations.get(condition, condition.lower())
            
            return f"El clima en {location.title()}: {temp_c}°C (sensación térmica {feels_like}°C), {condition_es}, humedad {humidity}%."
        else:
            return f"No pude obtener el clima de '{location}'. Verifica el nombre de la ciudad."
    except Exception as e:
        print(f"Error clima: {e}")
        return "No pude conectarme al servicio de clima. Revisa tu conexión a internet."

def get_news(source="google"):
    """Obtener noticias con mejor formato"""
    rss_feeds = {
        "google": "https://news.google.com/rss?hl=es&gl=ES&ceid=ES:es",
        "bbc": "http://feeds.bbci.co.uk/mundo/rss.xml",
        "elpais": "https://feeds.elpais.com/elpais/portada.xml",
        "cnn": "http://cnnespanol.cnn.com/feed/"
    }
    
    url = rss_feeds.get(source.lower(), rss_feeds["google"])
    
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            headlines = [entry.title for entry in feed.entries[:5]]
            source_name = source.upper() if source != "google" else "Google Noticias"
            return f"Últimas noticias de {source_name}: {'. '.join(headlines)}."
        else:
            return "No pude obtener noticias en este momento. Intenta más tarde."
    except Exception as e:
        print(f"Error noticias: {e}")
        return "Error al conectar con el servicio de noticias."

def get_location(query):
    """Búsqueda de ubicación mejorada"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
        headers = {'User-Agent': 'BaroAssistant/2.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                place = data[0]
                display_name = place['display_name']
                lat = float(place['lat'])
                lon = float(place['lon'])
                return f"'{query.title()}' está ubicado en: {display_name}. Coordenadas: latitud {lat:.4f}, longitud {lon:.4f}."
            else:
                return f"No encontré la ubicación de '{query}'. Intenta ser más específico."
        else:
            return "Error al buscar la ubicación. Intenta de nuevo."
    except Exception as e:
        print(f"Error ubicación: {e}")
        return "No pude buscar esa ubicación. Verifica tu conexión."

def learn_new(topic, info):
    """Aprender nueva información"""
    conn = sqlite3.connect('baro.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO knowledge (topic, info, category, keywords) VALUES (?, ?, ?, ?)", 
             (topic.lower(), info, "usuario", topic.lower()))
    conn.commit()
    conn.close()
    return f"¡Perfecto! Aprendí sobre '{topic}'. Ahora puedes preguntarme sobre esto cuando quieras."

def get_user_location():
    """Obtener ubicación del usuario usando su IP"""
    try:
        # Usar un servicio de geolocalización por IP
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            city = data.get('city', 'Desconocida')
            country = data.get('country_name', '')
            latitude = data.get('latitude', 0)
            longitude = data.get('longitude', 0)
            timezone = data.get('timezone', '')
            
            return {
                'city': city,
                'country': country,
                'latitude': latitude,
                'longitude': longitude,
                'timezone': timezone,
                'full_location': f"{city}, {country}"
            }
    except Exception as e:
        print(f"Error obteniendo ubicación: {e}")
    
    return {
        'city': 'La Habana',
        'country': 'Cuba',
        'latitude': 23.1136,
        'longitude': -82.3666,
        'timezone': 'America/Havana',
        'full_location': 'La Habana, Cuba'
    }

def calculate_expression(expr):
    """Calculadora mejorada con validación"""
    try:
        # Limpiar expresión
        expr = expr.strip()
        
        # Validar caracteres permitidos
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expr):
            return None
        
        # Evaluar de forma segura
        result = eval(expr, {"__builtins__": {}}, {})
        return result
    except:
        return None

# ============= PROCESADOR PRINCIPAL MEJORADO =============
def process_command(command):
    """Procesador de comandos principal con IA mejorada"""
    original_command = command
    command = command.lower().strip()
    
    # Detectar activación
    activation_words = ["baro", "varo"]
    activated = False
    for word in activation_words:
        if command.startswith(word):
            command = command[len(word):].strip()
            activated = True
            break
    
    if not activated:
        return "Di 'Baro' o 'Varo' al inicio para activarme."
    
    if not command:
        return "¿En qué puedo ayudarte? Puedes preguntarme sobre cualquier tema, el clima, noticias, hacer cálculos y mucho más."
    
    response = ""
    intent, confidence = nlp.detect_intent(command)
    
    # === COMANDO APRENDER ===
    if "aprende" in command or "recuerda" in command:
        parts = command.split(":", 1)
        if len(parts) == 2:
            topic_part = parts[0]
            info = parts[1].strip()
            topic = topic_part.replace("aprende", "").replace("recuerda", "").strip()
            if topic and info:
                response = learn_new(topic, info)
            else:
                response = "Para enseñarme, di: 'Baro aprende [tema]: [información]'. Por ejemplo: 'Baro aprende python: es un lenguaje de programación'."
        else:
            response = "Para enseñarme algo nuevo, usa este formato: 'Baro aprende [tema]: [información]'."
    
    # === SALUDOS ===
    elif intent == "saludo":
        responses = [
            "¡Hola! ¿En qué puedo ayudarte hoy?",
            "¡Hola! Soy Baro, tu asistente. ¿Qué necesitas?",
            "¡Hola! Estoy aquí para ayudarte. ¿Qué te gustaría saber?",
            "¡Hola! Es un placer saludarte. ¿En qué puedo asistirte?"
        ]
        response = random.choice(responses)
    
    # === DESPEDIDAS ===
    elif intent == "despedida":
        responses = [
            "¡Hasta luego! Que tengas un excelente día.",
            "¡Adiós! Fue un placer ayudarte.",
            "¡Hasta pronto! Vuelve cuando me necesites.",
            "¡Chau! Cuídate mucho."
        ]
        response = random.choice(responses)
    
    # === IDENTIDAD ===
    elif intent == "identidad":
        response = "Soy Baro, tu asistente de voz inteligente, similar a Alexa. Puedo ayudarte con información, clima, noticias, cálculos, búsquedas en internet, reproducir música, contar chistes y mucho más. Tengo capacidad de aprender cosas nuevas que me enseñes. ¿En qué puedo ayudarte?"
    
    # === HORA Y FECHA ===
    elif intent == "hora" or "hora" in command or "qué hora" in command:
        now = datetime.datetime.now()
        hora_12 = now.strftime('%I:%M %p')
        hora_24 = now.strftime('%H:%M')
        response = f"Son las {hora_24} ({hora_12})."
    
    elif intent == "fecha" or "fecha" in command or "qué día" in command or ("día" in command and "hoy" in command):
        now = datetime.datetime.now()
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        dia_semana = dias[now.weekday()]
        mes = meses[now.month - 1]
        response = f"Hoy es {dia_semana}, {now.day} de {mes} de {now.year}."
    
    # === CLIMA ===
    elif intent == "clima":
        location = nlp.extract_query(command, "clima")
        if not location or location in ["hoy", "ahora", "actual"]:
            location = "La Habana"
        response = get_weather(location)
    
    # === BÚSQUEDAS EN INTERNET ===
    elif intent == "buscar":
        query = nlp.extract_query(command, "buscar")
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            response = f"Abriendo Google para buscar '{query}'."
        else:
            response = "¿Qué quieres que busque en internet?"
    
    # === YOUTUBE ===
    elif intent == "youtube":
        query = nlp.extract_query(command, "youtube")
        if query:
            url = f"https://www.youtube.com/results?search_query={query}"
            webbrowser.open(url)
            response = f"Abriendo YouTube para buscar '{query}'."
        else:
            webbrowser.open("https://www.youtube.com")
            response = "Abriendo YouTube."
    
    # === NAVEGADOR ===
    elif "navegador" in command or "chrome" in command or "browser" in command:
        webbrowser.open("https://www.google.com")
        response = "Abriendo el navegador web."
    
    # === CALCULADORA ===
    elif intent == "calculadora":
        query = nlp.extract_query(command, "calculadora")
        result = calculate_expression(query)
        if result is not None:
            response = f"El resultado de {query} es {result}."
        else:
            try:
                subprocess.run(['gnome-calculator'], timeout=1)
                response = "Abriendo la calculadora."
            except:
                webbrowser.open("https://www.google.com/search?q=calculadora")
                response = "Abriendo calculadora web."
    
    # === CHISTES ===
    elif intent == "chiste":
        jokes = [
            "¿Por qué el libro de matemáticas está triste? Porque tiene muchos problemas.",
            "¿Qué hace una abeja en el gimnasio? ¡Zumba!",
            "¿Por qué los pájaros no usan Facebook? Porque ya tienen Twitter.",
            "¿Qué le dice un 0 a un 8? Bonito cinturón.",
            "¿Por qué el programador se fue al médico? Porque tenía un virus... ¡y no era de computadora!",
            "¿Cómo se llama el campeón de apnea japonés? Tokofondo.",
            "¿Qué le dice una iguana a su hermana gemela? Iguanita tú.",
            "¿Por qué el tomate se sonroja? Porque ve a la ensalada sin vestir.",
            "¿Qué le dice una pared a otra pared? Nos vemos en la esquina.",
            "¿Cuál es el colmo de un electricista? Que su esposa se llame Luz y sus hijos le sigan la corriente.",
            "¿Qué le dice el número 3 al número 30? Para ser como yo, tienes que ser sincero.",
            "¿Por qué la escoba está feliz? Porque se barre de la risa.",
            "¿Cómo se despiden los químicos? Ácido un placer.",
            "¿Qué hace un perro con un taladro? Taladrando.",
            "¿Cuál es el café más peligroso del mundo? El ex-preso."
        ]
        response = random.choice(jokes)
    
    # === NOTICIAS ===
    elif intent == "noticias":
        source = "google"
        if "bbc" in command:
            source = "bbc"
        elif "pais" in command or "elpais" in command:
            source = "elpais"
        elif "cnn" in command:
            source = "cnn"
        response = get_news(source)
    
    # === UBICACIÓN DEL USUARIO ===
    elif any(phrase in command for phrase in ["dónde estoy", "donde estoy", "mi ubicación", "mi ubicacion", "mi localización", "localización actual"]):
        location_data = get_user_location()
        response = f"Según mi información, estás en {location_data['full_location']}. Tu zona horaria es {location_data['timezone']}."
    
    # === BÚSQUEDA DE UBICACIONES ===
    elif intent == "ubicacion" or any(phrase in command for phrase in ["dónde queda", "dónde está", "ubicación de", "cómo llegar"]):
        query = nlp.extract_query(command, "ubicacion")
        if query:
            response = get_location(query)
        else:
            response = "¿Qué ubicación quieres buscar? Por ejemplo: 'dónde queda el museo del Prado'."
    
    # === TRADUCCIÓN ===
    elif intent == "traducir":
        response = "La función de traducción estará disponible pronto. Por ahora puedes usar Google Translate en tu navegador."
    
    # === PREGUNTAS DE CONOCIMIENTO ===
    elif any(command.startswith(qw) for qw in nlp.question_words):
        # Detectar tipo de pregunta
        q_type, topic = nlp.detect_question_type(command)
        
        if topic:
            # Buscar en conocimiento local
            local_info, score = search_knowledge(topic)
            
            if local_info and score > 0.6:
                response = local_info
            else:
                # Buscar en Wikipedia
                response = search_wikipedia(topic)
        else:
            response = "No entendí tu pregunta. ¿Podrías reformularla? Por ejemplo: '¿Qué es la inteligencia artificial?' o '¿Quién fue Einstein?'"
    
    # === BÚSQUEDA GENERAL DE CONOCIMIENTO ===
    else:
        # Intentar buscar en conocimiento local primero
        local_info, score = search_knowledge(command)
        
        if local_info and score > 0.5:
            response = local_info
        else:
            # Si no hay coincidencia local, buscar en Wikipedia
            wiki_result = search_wikipedia(command)
            if "No encontré" not in wiki_result and "error" not in wiki_result.lower():
                response = wiki_result
            else:
                response = "No estoy seguro de qué me preguntas. Puedes: pedirme la hora, el clima, noticias, que busque en internet, reproduzca música, cuente un chiste, haga cálculos, o preguntarme sobre cualquier tema. También puedo aprender: di 'Baro aprende [tema]: [información]'."
    
    # Registrar interacción
    try:
        conn = sqlite3.connect('baro.db')
        c = conn.cursor()
        c.execute("INSERT INTO interactions (timestamp, command, response, intent, confidence) VALUES (?, ?, ?, ?, ?)",
                  (datetime.datetime.now().isoformat(), command, response, str(intent), confidence))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error guardando interacción: {e}")
    
    return response

# Inicializar base de datos
init_db()

# ============= APLICACIÓN FLASK =============
app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Baro - Asistente Inteligente v2.0</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 600px;
                width: 100%;
            }
            h1 {
                color: #667eea;
                text-align: center;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
                font-size: 0.9em;
            }
            .status-indicator {
                text-align: center;
                margin-bottom: 20px;
                padding: 15px;
                border-radius: 10px;
                background: #f0f0f0;
                font-weight: bold;
            }
            .status-indicator.recording {
                background: #ffebee;
                color: #c62828;
                animation: pulse 1.5s ease-in-out infinite;
            }
            .status-indicator.processing {
                background: #fff3e0;
                color: #ef6c00;
            }
            .status-indicator.ready {
                background: #e8f5e9;
                color: #2e7d32;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .mic-button {
                display: block;
                margin: 0 auto 30px;
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: none;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-size: 50px;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
            }
            .mic-button:hover:not(:disabled) {
                transform: scale(1.1);
                box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
            }
            .mic-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            .response-box {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 20px;
                min-height: 100px;
                margin-bottom: 20px;
                line-height: 1.6;
            }
            .response-box p {
                margin-bottom: 10px;
                color: #333;
            }
            .response-label {
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }
            .tips {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }
            .tips h3 {
                color: #1976d2;
                margin-bottom: 10px;
                font-size: 1.1em;
            }
            .tips ul {
                margin-left: 20px;
                line-height: 1.8;
                color: #555;
            }
            .footer {
                text-align: center;
                margin-top: 20px;
                color: #999;
                font-size: 0.85em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 Baro AI</h1>
            <p class="subtitle">Asistente de Voz Inteligente v2.0</p>
            
            <div id="status" class="status-indicator ready">
                ✅ Listo para escuchar
            </div>
            
            <button id="record" class="mic-button">🎙️</button>
            
            <div class="response-box">
                <p class="response-label">Tu comando:</p>
                <p id="command">Presiona el micrófono y di "Baro" seguido de tu pregunta...</p>
                
                <p class="response-label" style="margin-top: 15px;">Respuesta de Baro:</p>
                <p id="response">Esperando tu comando...</p>
            </div>
            
            <div class="tips">
                <h3>💡 Ejemplos de lo que puedo hacer:</h3>
                <ul>
                    <li>"Baro, qué hora es"</li>
                    <li>"Baro, cómo está el clima en Madrid"</li>
                    <li>"Baro, qué es la inteligencia artificial"</li>
                    <li>"Baro, cuéntame un chiste"</li>
                    <li>"Baro, busca información sobre Cuba"</li>
                    <li>"Baro, reproduce música de salsa en YouTube"</li>
                    <li>"Baro, cuánto es 25 por 8"</li>
                    <li>"Baro, dame las últimas noticias"</li>
                    <li>"Baro, aprende python: es un lenguaje de programación"</li>
                </ul>
            </div>
            
            <p class="footer">Desarrollado con ❤️ | Powered by AI</p>
        </div>

        <script>
        let mediaRecorder;
        let audioChunks = [];
        const recordButton = document.getElementById('record');
        const status = document.getElementById('status');
        const commandText = document.getElementById('command');
        const responseText = document.getElementById('response');

        function updateStatus(state, message) {
            status.className = 'status-indicator ' + state;
            status.innerHTML = message;
        }

        function playBeep() {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.15);
        }

        recordButton.onclick = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });
                
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();
                audioChunks = [];
                
                updateStatus('recording', '🔴 Grabando... (5 segundos)');
                recordButton.disabled = true;
                commandText.textContent = 'Escuchando...';
                responseText.textContent = 'Procesando...';

                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });

                mediaRecorder.addEventListener('stop', async () => {
                    updateStatus('processing', '⏳ Procesando tu voz...');
                    
                    const audioBlob = new Blob(audioChunks, {type: 'audio/wav'});
                    const formData = new FormData();
                    formData.append('audio', audioBlob);
                    
                    try {
                        const res = await fetch('/process', {
                            method: 'POST', 
                            body: formData
                        });
                        const data = await res.json();
                        
                        commandText.textContent = data.recognized || 'No se reconoció el comando';
                        responseText.textContent = data.response;
                        
                        // Reproducir audio de respuesta si existe
                        if (data.audio && data.response && 
                            !data.response.includes("Di 'Baro'") && 
                            !data.response.includes("No entendí") &&
                            !data.response.includes("Error")) {
                            
                            playBeep();
                            
                            setTimeout(() => {
                                const audio = new Audio('data:audio/mp3;base64,' + data.audio);
                                audio.play().catch(e => console.log('Error audio:', e));
                            }, 300);
                        }
                        
                        updateStatus('ready', '✅ Listo para escuchar');
                    } catch (e) {
                        console.error('Error:', e);
                        responseText.textContent = 'Error al procesar. Intenta de nuevo.';
                        updateStatus('ready', '✅ Listo para escuchar');
                    }
                    
                    recordButton.disabled = false;
                    stream.getTracks().forEach(track => track.stop());
                });

                setTimeout(() => {
                    if (mediaRecorder.state === 'recording') {
                        mediaRecorder.stop();
                    }
                }, 5000);
                
            } catch (e) {
                console.error('Error micrófono:', e);
                updateStatus('ready', '❌ Error accediendo al micrófono');
                commandText.textContent = 'Error al acceder al micrófono. Verifica los permisos.';
                responseText.textContent = 'Por favor, permite el acceso al micrófono en tu navegador.';
                recordButton.disabled = false;
            }
        };
        </script>
    </body>
    </html>
    '''

@app.route('/process', methods=['POST'])
def process():
    """Procesar audio y retornar respuesta"""
    recognized_text = ""
    try:
        audio_file = request.files['audio']
        
        # Leer datos de audio
        audio_data = audio_file.read()
        
        try:
            # Intentar convertir de webm a wav usando AudioSegment
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
            audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
        except Exception as e:
            print(f"⚠️ Error convirtiendo audio: {e}")
            # Si falla la conversión, usar el audio tal como está
            wav_buffer = io.BytesIO(audio_data)
        
        # Reconocimiento de voz
        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8
        
        try:
            with sr.AudioFile(wav_buffer) as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.record(source)
                
                # Intentar reconocer en español
                try:
                    recognized_text = r.recognize_google(audio, language='es-ES')
                    print(f"✅ Reconocido: {recognized_text}")
                except sr.UnknownValueValue:
                    # Intentar con español latino
                    try:
                        recognized_text = r.recognize_google(audio, language='es-MX')
                        print(f"✅ Reconocido (MX): {recognized_text}")
                    except:
                        raise sr.UnknownValueError()
        except Exception as e:
            print(f"❌ Error de reconocimiento: {e}")
            raise sr.UnknownValueError()
            
        # Procesar comando
        response_text = process_command(recognized_text)
        
        # Generar audio solo para respuestas válidas
        audio_b64 = None
        should_speak = (
            response_text and 
            "Di 'Baro'" not in response_text and
            "No entendí" not in response_text and
            "Error" not in response_text and
            len(response_text) > 10
        )
        
        if should_speak:
            audio_data = generate_audio(response_text)
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
                'recognized': recognized_text,
                'response': response_text,
                'audio': audio_b64
            })
            
    except sr.UnknownValueError:
        return jsonify({
            'recognized': recognized_text or 'No detectado',
            'response': 'No entendí lo que dijiste. Habla más claro e intenta de nuevo.',
            'audio': None
        })
    except sr.RequestError as e:
        print(f"Error servicio reconocimiento: {e}")
        return jsonify({
            'recognized': recognized_text or 'Error',
            'response': 'Error en el servicio de reconocimiento. Verifica tu conexión a internet.',
            'audio': None
        })
    except Exception as e:
        print(f"Error general: {e}")
        return jsonify({
            'recognized': recognized_text or 'Error',
            'response': f'Error procesando tu solicitud. Intenta de nuevo.',
            'audio': None
        })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 BARO AI - ASISTENTE INTELIGENTE v2.0")
    print("=" * 60)
    print("✅ Sistema de NLP mejorado activado")
    print("✅ Base de conocimientos expandida cargada")
    print("✅ Búsqueda inteligente habilitada")
    print("✅ Integración con Wikipedia optimizada")
    print("=" * 60)
    print("🌐 Servidor iniciando en http://localhost:8000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8000, debug=True)
