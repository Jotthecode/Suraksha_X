// Option sets and validators shared by sign-up and Settings. Rules mirror the server (/api/register).

export const GENDERS = ['Female', 'Male', 'Other', 'Prefer not to say'];
export const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
export const RELATIONS = ['Mother', 'Father', 'Sister', 'Brother', 'Spouse', 'Friend', 'Other'];

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const isValidEmail = (email) => EMAIL_RE.test(String(email || '').trim().toLowerCase());

/** Local 10-digit mobile number without +91 / leading 0 (same as the server's _phone_digits). */
export const phoneDigits = (phone) => {
  let digits = String(phone || '').replace(/\D/g, '');
  if (digits.length === 12 && digits.startsWith('91')) digits = digits.slice(2);
  return digits.length === 11 ? digits.replace(/^0+/, '') : digits;
};

export const isValidPhone = (phone) => phoneDigits(phone).length === 10;

/** Split "YYYY-MM-DD" into { day, month, year } strings for the three DOB inputs. */
export const splitDob = (value) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ''));
  return m ? { day: m[3], month: m[2], year: m[1] } : { day: '', month: '', year: '' };
};

/**
 * Validate the DOB inputs. Returns { value, error }: value is "YYYY-MM-DD" or '' when all empty.
 */
export const parseDob = ({ day, month, year }) => {
  const d = String(day || '').trim();
  const m = String(month || '').trim();
  const y = String(year || '').trim();
  if (!d && !m && !y) return { value: '', error: '' };
  if (!/^\d{1,2}$/.test(d) || !/^\d{1,2}$/.test(m) || !/^\d{4}$/.test(y)) {
    return { value: '', error: 'Enter date as DD / MM / YYYY' };
  }
  const dn = Number(d);
  const mn = Number(m);
  const yn = Number(y);
  const date = new Date(yn, mn - 1, dn);
  if (date.getFullYear() !== yn || date.getMonth() !== mn - 1 || date.getDate() !== dn) {
    return { value: '', error: 'Enter a real date' };
  }
  if (yn < 1900 || date > new Date()) return { value: '', error: 'Enter a valid date of birth' };
  const pad = (n) => String(n).padStart(2, '0');
  return { value: `${yn}-${pad(mn)}-${pad(dn)}`, error: '' };
};

/** "1998-04-21" -> "21/04/1998" for display. */
export const formatDob = (value) => {
  const { day, month, year } = splitDob(value);
  return day ? `${day}/${month}/${year}` : '';
};
