PRAGMA foreign_keys = ON;

UPDATE users
SET professional_category = CASE professional_category
    WHEN 'doctor' THEN '{"conceptId":"309343006","tag":"occupation","term":"Physician"}'
    WHEN 'Physician' THEN '{"conceptId":"309343006","tag":"occupation","term":"Physician"}'
    WHEN 'Geriatrics specialist' THEN '{"conceptId":"90655003","tag":"occupation","term":"Geriatrics specialist"}'
    WHEN 'Obstetrician and gynaecologist' THEN '{"conceptId":"309367003","tag":"occupation","term":"Obstetrician and gynaecologist"}'
    WHEN 'Paediatrician' THEN '{"conceptId":"82296001","tag":"occupation","term":"Paediatrician"}'
    WHEN 'Surgeon' THEN '{"conceptId":"304292004","tag":"occupation","term":"Surgeon"}'
    WHEN 'Dentist' THEN '{"conceptId":"106289002","tag":"occupation","term":"Dentist"}'
    WHEN 'Nurse' THEN '{"conceptId":"106292003","tag":"occupation","term":"Nurse"}'
    ELSE professional_category
END
WHERE professional_category IS NOT NULL
  AND substr(trim(professional_category), 1, 1) != '{';

UPDATE users
SET gender = CASE gender
    WHEN 'female' THEN '{"conceptId":"248152002","tag":"gender","term":"Female"}'
    WHEN 'Female' THEN '{"conceptId":"248152002","tag":"gender","term":"Female"}'
    WHEN 'Indeterminate sex' THEN '{"conceptId":"32570681000036106","tag":"gender","term":"Indeterminate sex"}'
    WHEN 'Intersex' THEN '{"conceptId":"32570691000036108","tag":"gender","term":"Intersex"}'
    WHEN 'male' THEN '{"conceptId":"248153007","tag":"gender","term":"Male"}'
    WHEN 'Male' THEN '{"conceptId":"248153007","tag":"gender","term":"Male"}'
    WHEN 'Transsexual' THEN '{"conceptId":"407374003","tag":"gender","term":"Transsexual"}'
    WHEN 'Gender unknown' THEN '{"conceptId":"394743007","tag":"gender","term":"Gender unknown"}'
    ELSE gender
END
WHERE gender IS NOT NULL
  AND substr(trim(gender), 1, 1) != '{';

UPDATE users
SET preferred_language = CASE preferred_language
    WHEN 'english' THEN '{"conceptId":"297487008","tag":"language","term":"English"}'
    WHEN 'English' THEN '{"conceptId":"297487008","tag":"language","term":"English"}'
    WHEN 'hindi' THEN '{"conceptId":"161143006","tag":"language","term":"Hindi"}'
    WHEN 'Hindi' THEN '{"conceptId":"161143006","tag":"language","term":"Hindi"}'
    WHEN 'Bengali' THEN '{"conceptId":"161141008","tag":"language","term":"Bengali"}'
    ELSE preferred_language
END
WHERE preferred_language IS NOT NULL
  AND substr(trim(preferred_language), 1, 1) != '{';

UPDATE users
SET relationship_to_patient = CASE relationship_to_patient
    WHEN 'parent' THEN '{"conceptId":"303071001","tag":"relationship","term":"Family member"}'
    WHEN 'spouse' THEN '{"conceptId":"303071001","tag":"relationship","term":"Family member"}'
    WHEN 'Family member' THEN '{"conceptId":"303071001","tag":"relationship","term":"Family member"}'
    WHEN 'Neighbour' THEN '{"conceptId":"427568008","tag":"relationship","term":"Neighbour"}'
    WHEN 'Private nurse' THEN '{"conceptId":"158998005","tag":"relationship","term":"Private nurse"}'
    WHEN 'Maid' THEN '{"conceptId":"308225000","tag":"relationship","term":"Maid"}'
    WHEN 'Driver' THEN '{"conceptId":"106538001","tag":"relationship","term":"Driver"}'
    WHEN 'Servant' THEN '{"conceptId":"159725002","tag":"relationship","term":"Servant"}'
    WHEN 'friend' THEN '{"conceptId":"113163005","tag":"relationship","term":"Friend"}'
    WHEN 'Friend' THEN '{"conceptId":"113163005","tag":"relationship","term":"Friend"}'
    WHEN 'Colleague' THEN '{"conceptId":"32570881000036107","tag":"relationship","term":"Colleague"}'
    WHEN 'Acquaintance' THEN '{"conceptId":"48385004","tag":"relationship","term":"Acquaintance"}'
    WHEN 'Caregiver' THEN '{"conceptId":"133932002","tag":"relationship","term":"Caregiver"}'
    ELSE relationship_to_patient
END
WHERE relationship_to_patient IS NOT NULL
  AND substr(trim(relationship_to_patient), 1, 1) != '{';
