from datetime import date
import datetime
import numpy as np
import matplotlib.pyplot as plt
import wave
import librosa
import keras



def recognition():
    print(date.today())
    now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha = now[:10].replace("-","")
    hora = now[11:19].replace(":","")
    hora = int(hora)
    archivo_voz = []
    for i in range(1000):
        filename = fecha + "_" + str(hora) + ".wav"
        try: 
            a = librosa.core.load('./rec_voice_audios/'+filename)
            archivo_voz.append(a[0])
            print(a)
            break

        except FileNotFoundError:
            hora-=1
            continue


    ##comienza procesamiento
    archivo_spec = []
    for file in archivo_voz:
        a = create_mel_spectrogram(file)
        archivo_spec.append(a)
    

    model = keras.models.load_model('./modeloHM.h5')
    #Hace cortes (segmentos) en el test
    archivo_segment = []
    for spec in archivo_spec:
        x_test=[]
        y_test=[]
        for segment in range(0,spec.shape[1]-10,10):
            x_test.append(spec[:,segment:segment+10].reshape((128,10,1)))
            y_test.append([1,0])
        #ENDFOR
        x_test=np.array(x_test)
        prediccion=np.round(model.predict(x_test))
        prediccion=[x[0] for x in prediccion]
        hombres=[x for x in prediccion if x == 1]
        mujeres=[x for x in prediccion if x == 0]
        print("Porcentaje hombre: ",(len(hombres)/len(prediccion))*100,"Porcentaje mujer: ",(len(mujeres)/len(prediccion))*100)
        print()
    #ENDFOR







#Calcula el esprectro mel de la señal
def mel_spectrogram(wav, sr, db=True, n_fft=2**10, **kwargs):
    M = librosa.feature.melspectrogram(wav, sr=sr, n_fft=n_fft, **kwargs)
    if db:                                                               
       return librosa.power_to_db(M, ref=np.max)                        
    else:                                                                
       return M     
#ENDDEF


#Crear el espectrograma
def create_mel_spectrogram(wav_file):                        
   #wave, samplerate = read_wav(wav_file)                    
   melspec = mel_spectrogram(wav_file, sr=16000, n_fft=1024)  
   return np.abs(melspec) / np.linalg.norm(np.abs(melspec)) 
#ENDDEF
