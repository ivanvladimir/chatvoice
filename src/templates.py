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
        </tr>
    </thead>
    <tbody>
    {0}
    </tbody>
</table>"""

ROW_TABLE_CONVERSATION="""\
        <tr><td>{}</td><td><a href="execute/{}" class="button primary">Ejecutar</a></td></tr>"""
