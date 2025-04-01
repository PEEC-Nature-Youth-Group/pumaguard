from playsound3 import playsound

def play_sound(file_path):
    """
    Play a sound file using the USB speaker.
    
    Args:
        file_path (str): Path to the sound file.
    """
    playsound(file_path)

play_sound('/home/peec/pumaguard/scripts/forest-ambience-296528.mp3')
