with open('src/pages/index.html') as f:
    INDEX=f.read()


with open('src/pages/conversation.html') as f:
    CONVERSATION=f.read()

TABLE_CONVERSATION="""\
    <table class="stripped hoverable">
    <caption>Conversasiones disponibles</caption>
    <thead>
        <tr>
            <th>Path</th>
            <th>Acciones</th>
            <th>Opciones</th>
        </tr>
    </thead>
    <tbody>
    {0}
    </tbody>
</table>"""

ROW_TABLE_CONVERSATION="""\
        <tr><td>{0}</td><td><a href="execute/{1}" class="button primary" id='href{2}'>Ejecutar</a></td><td>
          <input onchange="set_asr({2})" type="checkbox" id="asr{2}" name="asr{2}"><label for="asr{2}">Reconocedor de voz</label><br>
          <input onchange="set_tts({2})" type="radio" id="tts{2}" name="tts{2}" value="no" checked><label for="tts{2}">Sin sintesis</label><br>
          <input onchange="set_tts({2})" type="radio" id="tts{2}local" name="tts{2}" value="local"><label for="tts{2}">Sintesis local</label><br>
          <input onchange="set_tts({2})" type="radio" id="tts{2}google" name="tts{2}" value="google"><label for="tts{2}">Sintesis google</label><br>
        </td></tr>"""
