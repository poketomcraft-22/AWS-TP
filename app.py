from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
import sys
import os

# --- CONFIGURATION REQUISE ---
# >>> MODIFIEZ SEULEMENT CETTE LIGNE <<<
# Le nom du profil AWS que vous avez configuré localement (ex: pour AssumeRole).
PROFILE_NAME = "voclabs/user4457538=t.dulong@ecole-ipssi.net" 
# -----------------------------

app = Flask(__name__)
# Une clé secrète est nécessaire pour utiliser 'flash' (messages d'alerte)
app.secret_key = 'super_secret_key_dev' 

# Initialisation de la session AWS
try:
    # Boto3 lit la configuration du profil spécifié (y compris l'ARN pour AssumeRole).
    aws_session = boto3.Session(profile_name=PROFILE_NAME)
    
    # On détermine la région de travail à partir de la session
    REGION_NAME = aws_session.region_name
    print(f"Session AWS établie via le profil '{PROFILE_NAME}' dans la région '{REGION_NAME}'.")
    
except Exception as e:
    print("\n" + "="*50)
    print("ERREUR FATALE: Échec de l'établissement de la session AWS.")
    print(f"L'erreur est : {e}")
    print(f"Vérifiez si le profil '{PROFILE_NAME}' est correctement configuré (avec le 'role_arn').")
    print("="*50)
    sys.exit(1)


# ----------------------------------------------------------------------
# ROUTES COMMUNES
# ----------------------------------------------------------------------

@app.route('/')
def index():
    """Page d'accueil."""
    return render_template('index.html')

# ----------------------------------------------------------------------
# SECTION EC2
# ----------------------------------------------------------------------

@app.route('/ec2_list')
def ec2_list():
    """Liste toutes les instances EC2 et leur état."""
    try:
        ec2_resource = aws_session.resource('ec2')
        instances_data = []
        for instance in ec2_resource.instances.all():
            name = next((tag['Value'] for tag in instance.tags if tag['Key'] == 'Name'), 'N/A')
            instances_data.append({
                'id': instance.id,
                'state': instance.state['Name'],
                'name': name
            })
        return render_template('ec2_list.html', instances=instances_data)

    except Exception as e:
        flash(f"Erreur lors de la liste des instances EC2: {e}", 'error')
        return redirect(url_for('index'))

@app.route('/ec2_action/<action>/<instance_id>', methods=['POST'])
def ec2_action(action, instance_id):
    """Effectue l'action Démarrer/Arrêter sur une instance EC2."""
    ec2_client = aws_session.client('ec2')
    try:
        if action == 'start':
            ec2_client.start_instances(InstanceIds=[instance_id])
            flash(f"Démarrage de l'instance {instance_id} lancé.", 'success')
        elif action == 'stop':
            ec2_client.stop_instances(InstanceIds=[instance_id])
            flash(f"Arrêt de l'instance {instance_id} lancé.", 'success')
        
    except ec2_client.exceptions.ClientError as e:
        flash(f"Erreur EC2: {e.response['Error']['Message']}", 'error')
    except Exception as e:
        flash(f"Erreur inattendue: {e}", 'error')
        
    return redirect(url_for('ec2_list'))

# ----------------------------------------------------------------------
# SECTION S3
# ----------------------------------------------------------------------

@app.route('/s3_list')
def s3_list():
    """Liste les buckets S3."""
    try:
        s3_client = aws_session.client('s3')
        response = s3_client.list_buckets()
        buckets = [b['Name'] for b in response['Buckets']]
        return render_template('s3_list.html', buckets=buckets)
    except Exception as e:
        flash(f"Erreur lors de la liste des buckets S3: {e}", 'error')
        return redirect(url_for('index'))


@app.route('/s3_create', methods=['GET', 'POST'])
def s3_create():
    """Gère la création d'un nouveau bucket S3."""
    if request.method == 'POST':
        bucket_name = request.form.get('bucket_name').lower()
        if not bucket_name:
            flash("Le nom du bucket est requis.", 'error')
            return redirect(url_for('s3_create'))
            
        try:
            s3_client = aws_session.client('s3')
            # Utilise la région déterminée par la session pour la création du bucket
            s3_client.create_bucket(
                Bucket=bucket_name, 
                CreateBucketConfiguration={'LocationConstraint': REGION_NAME}
            )
            flash(f"Bucket '{bucket_name}' créé avec succès dans la région {REGION_NAME}.", 'success')
            return redirect(url_for('s3_list'))
            
        except s3_client.exceptions.ClientError as e:
            flash(f"Erreur S3: {e.response['Error']['Message']}", 'error')
        except Exception as e:
            flash(f"Erreur inattendue: {e}", 'error')
            
    return render_template('s3_create.html')


@app.route('/s3_delete_confirm/<bucket_name>')
def s3_delete_confirm(bucket_name):
    """Page de confirmation avant suppression."""
    return render_template('s3_delete_confirm.html', bucket_name=bucket_name)

@app.route('/s3_delete/<bucket_name>', methods=['POST'])
def s3_delete(bucket_name):
    """Supprime un bucket S3 et son contenu (attention !)."""
    s3_resource = aws_session.resource('s3')
    try:
        bucket = s3_resource.Bucket(bucket_name)
        
        # 1. Supprimer tous les objets dans le bucket
        bucket.objects.all().delete()
        
        # 2. Supprimer le bucket lui-même
        bucket.delete()
        
        flash(f"Bucket '{bucket_name}' et son contenu supprimés avec succès.", 'success')
    except s3_resource.meta.client.exceptions.ClientError as e:
        flash(f"Erreur S3: {e.response['Error']['Message']}", 'error')
    except Exception as e:
        flash(f"Erreur inattendue: {e}", 'error')
        
    return redirect(url_for('s3_list'))


@app.route('/s3_upload/<bucket_name>', methods=['POST'])
def s3_upload(bucket_name):
    """Gère l'upload de fichier dans un bucket."""
    if 'file' not in request.files:
        flash("Aucun fichier sélectionné.", 'error')
        return redirect(url_for('s3_list'))
        
    file = request.files['file']
    if file.filename == '':
        flash("Nom de fichier vide.", 'error')
        return redirect(url_for('s3_list'))
        
    s3_client = aws_session.client('s3')
    try:
        # Upload du fichier
        s3_client.upload_fileobj(
            file,
            bucket_name,
            file.filename  # Clé S3 = nom du fichier
        )
        flash(f"Fichier '{file.filename}' téléchargé dans le bucket '{bucket_name}'.", 'success')
    except Exception as e:
        flash(f"Erreur d'upload S3: {e}", 'error')
        
    return redirect(url_for('s3_list'))

if __name__ == '__main__':
    # Flask exige que le dossier 'static' et 'templates' existent
    if not os.path.isdir('static'):
        os.mkdir('static')
    if not os.path.isdir('templates'):
        os.mkdir('templates')

    # Important pour le déploiement sur EC2:
    # Pour que l'interface soit accessible via l'IP publique de l'EC2, il faut lier Flask à 0.0.0.0
    print("Démarrage de l'application Flask sur http://0.0.0.0:5000/")
    app.run(debug=True, host='0.0.0.0')