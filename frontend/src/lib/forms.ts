export function validateField(event: Event) {
    const field = event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
    field.setCustomValidity(field.validity.valueMissing ? "Completa este campo." : "Revisa el formato.");
}

export function clearValidation(event: Event) {
    const field = event.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
    field.setCustomValidity("");
}
