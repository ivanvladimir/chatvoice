def ec_slot(self, slots):
    """Prints the values of the slots"""
    for slot in slots:
        if slot in self.slots:
            self.console.print(f"[blue]{slot}[/blue] → [bold]{self.slots[slot]}[/bold]")
        else:
            self.console.print(f"[red]Slot [bold]{slot}[/bold] not found [/red]")


def ec_slots(self):
    """Prints the values of the slots"""
    for slot, value in self.slots.items():
        self.console.print(f"[blue]{slot}[/blue] → [bold]{value}[/bold]")
