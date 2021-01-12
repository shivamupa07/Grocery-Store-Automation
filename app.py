from flask import Flask, render_template, flash, request, redirect, url_for, session, logging
from dbconnect import Connection
from iot import iotConnection
import os
import getpass
import datetime
import random
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/')
@app.route('/index.html')
def index():
    if 'user_phone' in session:
        return redirect('/welcome')
    else:
        return render_template('index.html')

@app.route('/login')
def login():
    if 'user_phone' in session:
        return redirect('/welcome')
    else:
        iotConnection()
        return render_template('login.html')

def password_hash(pswd):
    salt = os.urandom(32) # Remember this

    key = hashlib.pbkdf2_hmac('sha256',pswd.encode('utf-8'),salt,100000)
    password = salt + key
    return password

def password_hash_validation(new_password,old_password):

    
    old_password = bytes(old_password)
    salt = old_password[:32]
    new_key = hashlib.pbkdf2_hmac('sha256',new_password.encode('utf-8'),salt,100000)

    password = salt + new_key
    return password

@app.route('/signup')
def signup():
    if 'user_phone' in session:
        return redirect('/welcome')
    else:
        return render_template('signup.html')

@app.route('/welcome')
def welcome():
    if 'user_phone' in session:
        name = session['user_name']
        fname = session['user_fname']
        if 'user_gender' in session:
            flash('Successfully Logged-In')
            session.pop('user_gender')
            return render_template('welcome.html', name=name, fname=fname)
        else:
            return render_template('welcome.html', name = name)
    else:
        return redirect('/')

@app.route('/about')
def about():
        return render_template('about.html')

@app.route('/login_validation', methods=['POST'])
def login_validation():
    if(request.method == 'POST'):
        phone=str(request.form.get('phone'))
        password=str(request.form.get('password'))
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select password from customer where phone = {}".format(phone))
            x = cur.fetchall()
            if len(x)>0 :
                key = x[0][0]
                new_key = password_hash_validation(password,key)
                if key == new_key:
                    cur.execute("select * from customer where phone = {}".format(phone))
                    user = cur.fetchall()
                    session['user_name'] = user[0][0]
                    session['user_email'] = user[0][1]
                    session['user_gender'] = user[0][3]
                    session['user_phone'] = user[0][4]
                    cur.execute("SELECT SUBSTRING_INDEX( name, ' ', 1 ) from customer where phone = {}".format(phone))
                    user = cur.fetchall()
                    session['user_fname'] = user[0][0]
                    return redirect(url_for("welcome"))
                else:
                    flash('Invalid Username/Password!!')
                    return redirect(url_for("login"))
            else:
                flash('Invalid Username/Password!!')
                return redirect(url_for("login"))

        except Exception as e:
            con.rollback()
            print("Error:",e)
            
        finally:
            cur.close()
            con.close()
    


@app.route('/register', methods=['POST'])
def register():
    if(request.method == 'POST'):
        name=str(request.form.get('name'))
        email=str(request.form.get('email'))
        password=str(request.form.get('password'))
        gender=str(request.form.get('gender'))
        phone=str(request.form.get('phone'))
        password = password_hash(password)
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select * from customer where phone = {}".format(phone))
            user = cur.fetchall()
            if len(user)>0:
                flash('Mobile no. already registered, try Login!!')
                return redirect(url_for("signup"))
            else:
                cur.execute("insert into customer values(%s,%s,%s,%s,%s)",(name,email,password,gender,phone))
                con.commit()
                flash('Successfully Registered. Login here to continue')
                return redirect('/login')
        except Exception as e:
            con.rollback()
            print("Error:",e)
            return redirect('/signup')
        finally:
            cur.close()
            con.close()

@app.route('/logout')
def logout():
    session.pop('user_phone')
    session.pop('user_name')
    session.pop('user_fname')
    flash('Successfully logged out!!')
    return redirect('/login')

@app.route('/vendor')
@app.route('/purchase')
def purchase():
    return render_template('purchase.html')

@app.route('/newpurchase')
def newpurchase():
    if 'purchase_phone' in session:
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select item_name from item_info")
            names = cur.fetchall()
            item_name = inventory_name(names)
            cur.execute("select item_id from item_info")
            ids = cur.fetchall()
            item_id = inventory_id(ids)
            length = len(item_name)
            if len(item_name)>0:
                return render_template('new_purchase.html', length=length, names=item_name, ids=item_id)
            else:
                redirect('/purchase')
        except Exception as e:
            con.rollback()
            print("Error:",e)
            return redirect('/purchase')
        finally:
            cur.close()
            con.close()
    else:
        return redirect('/purchase')

@app.route('/purchase_validation', methods=['POST','GET'])
def purchase_validation():
    if(request.method == 'POST'):
        phone=str(request.form.get('phone'))
        session['purchase_phone'] = phone
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select * from customer where phone = {}".format(phone))
            user = cur.fetchall()
            cur.execute("select * from pending_transaction where phone = {}".format(phone))
            active = cur.fetchall()
            if len(active)>0:
                flash('!!!  Customer has a Pending Transaction  !!!')
                return redirect(url_for("purchase"))
            else:
                if len(user)>0:
                    flash('Customer is Registered')
                    return redirect(url_for("newpurchase"))
                else:
                    flash('Customer is NOT Registered')
                    return redirect(url_for("newpurchase"))
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()

@app.route('/createpurchase', methods=['POST','GET'])
def create_purchase():
    if(request.method == 'POST'):
        name,qnty,id = name_list()
        name_str = name[0]
        qnty_str = qnty[0]
        id_str = id[0]
        phone = session['purchase_phone']
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        for i in range(1,len(name)):
            name_str = name_str+","+name[i]
        for i in range(1,len(qnty)):
            qnty_str = qnty_str+","+qnty[i]
        for i in range(1,len(id)):
            id_str = id_str+","+id[i]

        price_list = []
        total_price = 0.0
        for i in range(len(id)):
            item_price,total_price = calculate_price(id[i],qnty[i],total_price)
            price_list.append(str(item_price))

        price_str = price_list[0]
        for i in range(1,len(price_list)):
            price_str = price_str+","+price_list[i]
            
        trns_id = random_numbers(phone,date)
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("insert into pending_transaction(trns_id,phone,items_ids,items_names,items_qntys,items_price,total_price,date) values(%s,%s,%s,%s,%s,%s,%s,%s)",(trns_id,phone,id_str,name_str,qnty_str,price_str,total_price,date))
            con.commit()
            return redirect('/purchase')
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()
    else:
        return redirect('/purchase')

def random_numbers(phone,date):
    num = random.randrange(1000001, 10000000)
    rnum = "TNX"+str(num)
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select * from transactions where trns_id = '{}'".format(rnum))
        trns_id = cur.fetchall()
        if len(trns_id)>0:
            random_numbers(phone,date)
        else:
            cur.execute("insert into transactions values(%s,%s,%s)",(rnum,phone,date))
            con.commit()
            return rnum

    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()

def name_list():
    nameList = []
    qntyList = []
    idList = []
    try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select item_name from item_info")
            names = cur.fetchall()
            item_name = inventory_name(names)
            cur.execute("select item_id from item_info")
            ids = cur.fetchall()
            item_id = inventory_id(ids)
            for i in range(len(item_id)):
                checkBox = "check"+str(item_id[i])
                qntyBox = "qnty"+str(item_id[i])
                if (str(request.form.get(checkBox)))==str(item_id[i]):
                    if item_name[i] in nameList:
                        pass
                    else:
                        nameList.append(item_name[i])
                        new_qnty = str(request.form.get(qntyBox))
                        qntyList.append(new_qnty)
                        idList.append(str(item_id[i]))
            
    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()
    return nameList,qntyList,idList

def calculate_price(item_id,qnty,total_price):
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select price from item_price where item_id = {}".format(item_id))
        ftech_price = cur.fetchall()
        price = float(ftech_price[0][0])
        item_qnty = float(qnty)
        item_price = round((price * item_qnty),1)
        total_price = total_price + item_price
    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()
    return item_price,total_price

@app.route('/inventory')
def inventory():
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select item_name from item_info")
        name = cur.fetchall()
        item_name = inventory_name(name)
        cur.execute("select item_id from item_info")
        id = cur.fetchall()
        item_id = inventory_id(id)
        cur.execute("select image_loc from item_images")
        image = cur.fetchall()
        cur.execute("select qnty_mrsmnt,quantity from item_weight")
        weight = cur.fetchall()
        item_weight = inventory_weight(weight)
        item_image = inventory_image(image)
        cur.execute("select qnty_mrsmnt,price from item_price")
        qnty_price = cur.fetchall()
        item_price = inventory_price(qnty_price)
        length = len(item_name)
        if len(item_name)>0:
            return render_template('inventory.html', length=length, id=item_id, name=item_name, image=item_image, weight=item_weight, price=item_price)
        else:
            flash('Inventory is Empty!!')
            return render_template('inventory.html')
    except Exception as e:
        con.rollback()
        print("Error:",e)
        return render_template('inventory.html')
    finally:
        cur.close()
        con.close()

def inventory_id(item_id):
    idList = []
    for i in item_id:
        idList.extend(i)
    return idList

def inventory_image(image):
    imageList = []
    for i in image:
        imageList.extend(i)
    return imageList

def inventory_name(name):
    nameList = []
    for i in name:
        nameList.extend(i)
    return nameList

def inventory_weight(qnty_weight):
    weightList = []
    list1 = []
    for i in range(len(qnty_weight)):
            list2 = []
            for j in range(len(qnty_weight[i])):
                list2.append(qnty_weight[i][j])
            list1.append(list2)

    for i in range(len(list1)):
        for j in range(len(list1[i])):
            qnty = str(list1[i][1])
            if list1[i][0]=='kg':
                qnty = qnty + ' Kg remaining'
            else:
                qnty = qnty + ' Pieces remaining'
        weightList.append(qnty)

    return weightList

def inventory_price(qnty_price):
    priceList = []
    list1 = []
    for i in range(len(qnty_price)):
            list2 = []
            for j in range(len(qnty_price[i])):
                list2.append(qnty_price[i][j])
            list1.append(list2)

    for i in range(len(list1)):
        for j in range(len(list1[i])):
            price = str(list1[i][1])
            if list1[i][0]=='kg':
                price = price + ' Rs/Kg'
            else:
                price = price + ' Rs/Piece'
        priceList.append(price)

    return priceList

@app.route('/update_price')
def update_price():
    return render_template('update_price.html')

@app.route('/fetchdetails', methods=['POST','GET'])
def fetchdetails():
    if(request.method == 'POST'):
        item_id = request.form.get('itemid')
        session['item_id'] = item_id
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select item_name from inventory where item_id = {}".format(item_id))
            name = cur.fetchall()
            item_name = inventory_name(name)
            item_name = item_name[0]
            cur.execute("select qnty_mrsmnt,price from item_price where item_id = {}".format(item_id))
            qnty_price = cur.fetchall()
            item_price = inventory_price(qnty_price)
            item_price = item_price[0]
            itemid = item_id
            if len(name)>0:
                return render_template('updateprice.html', itemid=itemid, itemname=item_name, itemprice=item_price)
            else:
                flash('Item NOT FOUND!!')
                return render_template('update_price.html')
            
        except Exception as e:
            con.rollback()
            print("Error:",e)
            flash('Item NOT FOUND!!')
            return render_template('update_price.html')
        finally:
            cur.close()
            con.close()

@app.route('/validate_price', methods=['POST','GET'])
def validate_price():
    if(request.method == 'POST'):
        item_id = session['item_id']
        new_price = int(request.form.get('newprice'))
        if new_price > 0:
            try:
                con = Connection()
                cur = con.cursor(buffered=True)
                cur.execute("UPDATE inventory SET price = %s WHERE item_id = %s ",(new_price,item_id))
                con.commit()
                cur.execute("UPDATE item_price SET price = %s WHERE item_id = %s ",(new_price,item_id))
                con.commit()
                session.pop('item_id')
                flash('Price Updated Successfully')
                return redirect('/inventory')
            except Exception as e:
                con.rollback()
                flash(e)
                return redirect('/updateprice')
            finally:
                cur.close()
                con.close()
        
        else:
            flash('Please enter a value greater than 0 !!')
            return redirect('/updateprice')

@app.route('/history')
def vendor_history():
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select * from customer_history")
        x = cur.fetchall()
        x = x[::-1]
        phones,ids,names,qntys,prices,total_prices,dates = compute_history(x)
        ids,names,qntys,prices,dates = separate_comma(ids,names,qntys,prices,dates)
        qntys,prices,total_prices = qnty_mrsmnt(ids,qntys,prices,total_prices)
        length = len(phones)
        if len(phones)>0:
            return render_template('vendor_history.html', length=length, phone=phones, name=names, qnty=qntys, price=prices, total_price=total_prices, date=dates)
        else:
            flash('History is Empty!!')
            return redirect('/purchase')
    except Exception as e:
        con.rollback()
        print("Error:",e)
        flash('History is Empty!!')
        return redirect('/purchase')
    finally:
        cur.close()
        con.close()

@app.route('/order_history')
def customer_history():

    user_phone = session.get('user_phone')
    user_name = session.get('user_name')
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select * from customer_history where phone = {}".format(user_phone))
        x = cur.fetchall()
        x = x[::-1]
        phones,ids,names,qntys,prices,total_prices,dates = compute_history(x)
        ids,names,qntys,prices,dates = separate_comma(ids,names,qntys,prices,dates)
        qntys,prices,total_prices = qnty_mrsmnt(ids,qntys,prices,total_prices)
        length = len(phones)
        if len(phones)>0:
            return render_template('customer_history.html', length=length, user_name=user_name, name=names, qnty=qntys, price=prices, total_price=total_prices, date=dates)
        else:
            flash('History is Empty!!')
            return redirect('/welcome')
    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()

@app.route('/pending_customer')
def pending_customer():
    user_phone = session.get('user_phone')
    user_name = session.get('user_name')
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select * from pending_transaction where phone = {}".format(user_phone))
        x = cur.fetchall()
        if len(x)>0:
            trans_id = x[0][1]
            phones,ids,names,qntys,prices,total_prices,dates = pending_history(x)
            ids,names,qntys,prices,dates = separate_comma(ids,names,qntys,prices,dates)
            qntys,prices,total_prices = qnty_mrsmnt(ids,qntys,prices,total_prices)
            length = len(phones)
            if len(phones)>0:
                return render_template('pending.html', length=length, user_name=user_name, user_phone=user_phone, trans_id=trans_id, name=names, qnty=qntys, price=prices, total_price=total_prices, date=dates)
            else:
                flash('!! NO Active Order !!')
                return redirect('/order_history')
        else:
                flash('!! NO Active Order !!')
                return redirect('/order_history')
    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()

@app.route('/cust_trans_remove', methods=['POST','GET'])
def cust_trans_remove():
    if(request.method == 'POST'):
        phone = str(request.form.get('phone'))
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("delete from pending_transaction where phone = {}".format(phone))
            con.commit()
            cur.execute("delete from transactions where phone = {}".format(phone))
            con.commit()
            return redirect('/pending_customer')
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()

@app.route('/customer_pay', methods=['POST','GET'])
def customer_pay():
    if(request.method == 'POST'):
        phone = str(request.form.get('phone'))
        name = session.get('user_name')
        email = session.get('user_email')
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select * from pending_transaction where phone = {}".format(phone))
            x = cur.fetchall()
            trans_id = x[0][1]
            item_ids = x[0][3]
            item_names = x[0][4]
            item_qntys = x[0][5]
            item_prices = x[0][6]
            item_names,item_qntys,item_prices = separate_comma_customer(item_ids,item_names,item_qntys,item_prices)
            total_price = x[0][7]
            length = len(item_names)
            return render_template('payment.html',length=length, phone=phone, name=name, email=email, trans_id=trans_id, item_name=item_names,item_qnty=item_qntys, item_price=item_prices, total_price=total_price)
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()

@app.route('/payment', methods=['POST','GET'])
def payment():
    if(request.method == 'POST'):
        phone = str(request.form.get('phone'))
        paymentMethod = str(request.form.get('paymentMethod'))
        if paymentMethod == "debit-card":
            debitCheck = str(request.form.get('debitCheck'))
            if debitCheck == "debitCheck":
                nameCard = str(request.form.get('debitName'))
                numberCard = str(request.form.get('debitNumber'))
                cvvCard = str(request.form.get('debitCvv'))
                return redirect('/pending_customer')
            else:
                print("Card NOT Saved")
                return redirect('/pending_customer')
        
        if paymentMethod == "upi":
            upiId = str(request.form.get('upiId'))
            print(upiId)
            print("UPI Done")
            return redirect('/pending_customer')

def separate_comma_customer(item_id,item_name,item_qnty,item_price):
    
    qnty_msrmnt = []
    item_ids = item_id.split(",")
    item_names = item_name.split(",")
    item_qntys = item_qnty.split(",")
    item_prices = item_price.split(",")
    
    for i in range(len(item_ids)):
        msrmnt = find_mrsmnt(item_ids[i],item_qntys[i])
        qnty_msrmnt.append(msrmnt)

    return item_names,qnty_msrmnt,item_prices

def compute_history(x):
    phones = []
    ids = []
    names = []
    qntys = []
    prices = []
    total_prices = []
    dates = []
    for i in range(len(x)):
        phones.append(x[i][1])
        ids.append(x[i][2])
        names.append(x[i][3])
        qntys.append(x[i][4])
        prices.append(x[i][5])
        total_prices.append(x[i][6])
        dates.append(x[i][7])

    return phones,ids,names,qntys,prices,total_prices,dates

def pending_history(x):
    phones = []
    ids = []
    names = []
    qntys = []
    prices = []
    total_prices = []
    dates = []
    for i in range(len(x)):
        phones.append(x[i][2])
        ids.append(x[i][3])
        names.append(x[i][4])
        qntys.append(x[i][5])
        prices.append(x[i][6])
        total_prices.append(x[i][7])
        dates.append(x[i][8])

    return phones,ids,names,qntys,prices,total_prices,dates

def separate_comma(id,name,qnty,price,date):
    ids = []
    names = []
    qntys = []
    prices = []
    dates = []

    for i in range(len(id)):
        x = id[i].split(",")
        ids.append(x)

    for i in range(len(name)):
        x = name[i].split(",")
        names.append(x)
    
    for i in range(len(qnty)):
        x = qnty[i].split(",")
        qntys.append(x)
    
    for i in range(len(price)):
        x = price[i].split(",")
        prices.append(x)
    
    for i in range(len(date)):
        x = date[i].split("-")
        year = str(x[0])
        month = str(x[1])
        day = str(x[2])
        new_date = day+"-"+month+"-"+year
        dates.append(new_date)
    
    return ids,names,qntys,prices,dates

def qnty_mrsmnt(id,qnty,price,total_price):
    qntys = []
    prices = []
    total_prices = []
    for i in range(len(id)):
        list1 = []
        for j in range(len(id[i])):
            msrmnt = find_mrsmnt(id[i][j],qnty[i][j])
            list1.append(msrmnt)
        qntys.append(list1)
    for i in range(len(price)):
        list1 = []
        for j in range(len(price[i])):
            pric = str(price[i][j])
            pric = pric + " Rs"
            list1.append(pric)
        prices.append(list1)
    for i in range(len(total_price)):
        pric = str(total_price[i])
        pric = pric + " Rs"
        total_prices.append(pric)

    return qntys,prices,total_prices

def find_mrsmnt(id,qnty):
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select qnty_mrsmnt from item_weight where item_id = {}".format(id))
        x = cur.fetchall()
        qnty = str(qnty)
        if x[0][0]=='kg':
            qnty = qnty + ' Kg'
        else:
            qnty = qnty + ' Pieces'

        return qnty

    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()

@app.route('/pending_vendor')
def pending_vendor():
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select * from pending_transaction order by sl_no DESC")
        x = cur.fetchall()
        phones,ids,names,qntys,prices,total_prices,dates = pending_history(x)
        status = if_registered(phones)
        ids,names,qntys,prices,dates = separate_comma(ids,names,qntys,prices,dates)
        qntys,prices,total_prices = qnty_mrsmnt(ids,qntys,prices,total_prices)
        length = len(phones)
        if len(phones)>0:
            return render_template('pending_vendor.html', length=length, status=status, phone=phones, name=names, qnty=qntys, price=prices, total_price=total_prices, date=dates)
        else:
            flash('NO Pending Transactions!!')
            return redirect('/history')
    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()

def if_registered(phones):

    status_list = []
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        for phone in phones:
            cur.execute("select * from customer where phone = {}".format(phone))
            x = cur.fetchall()
            if len(x)>0:
                status = 1
                status_list.append(status)
            else:
                status = 0
                status_list.append(status)
        return status_list
    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()

@app.route('/trans_done', methods=['POST','GET'])
def trans_done():
    if(request.method == 'POST'):
        phone = str(request.form.get('phone'))
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select * from pending_transaction where phone = {}".format(phone))
            x = cur.fetchall()
            item_ids = x[0][3]
            item_qntys = x[0][5]
            item_ids,item_qntys = separate_comma_pending(item_ids,item_qntys)
            
            for i in range(len(item_ids)):
                update_inventory(item_ids[i],item_qntys[i])
            
            cur.execute("insert into customer_history select trns_id,phone,items_ids,items_names,items_qntys,items_price,total_price,date from pending_transaction where phone = {}".format(phone))
            con.commit()
            cur.execute("delete from pending_transaction where phone = {}".format(phone))
            con.commit()
            return redirect('/pending_vendor')
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()

def separate_comma_pending(id,qnty):
        
    ids = id.split(",")
    qntys = qnty.split(",")
    
    return ids,qntys

def update_inventory(item_id,new_qnty):
    try:
        con = Connection()
        cur = con.cursor(buffered=True)
        cur.execute("select quantity from inventory where item_id = {}".format(item_id))
        ftech_qnty = cur.fetchall()
        qnty = float(ftech_qnty[0][0])
        qnty = float(qnty)
        new_qnty = float(new_qnty)
        update_qnty = qnty - new_qnty
        cur.execute("UPDATE inventory SET quantity = %s WHERE item_id = %s ",(update_qnty,item_id))
        con.commit()
        cur.execute("UPDATE item_weight SET quantity = %s WHERE item_id = %s ",(update_qnty,item_id))
        con.commit()
    except Exception as e:
        con.rollback()
        print("Error:",e)
    finally:
        cur.close()
        con.close()
    return

@app.route('/trans_remove', methods=['POST','GET'])
def trans_remove():
    if(request.method == 'POST'):
        phone = str(request.form.get('phone'))
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("delete from pending_transaction where phone = {}".format(phone))
            con.commit()
            cur.execute("delete from transactions where phone = {}".format(phone))
            con.commit()
            return redirect('/pending_vendor')
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()

@app.route('/customer_list', methods=['POST','GET'])
def customer_list():
    if(request.method == 'POST'):
        search = str(request.form.get('search'))
        searchWith = str(request.form.get('searchWith'))
        if searchWith == "name":
            try:
                con = Connection()
                cur = con.cursor(buffered=True)
                cur.execute("select * from customer where locate('{}',name)".format(search))
                customer = cur.fetchall()
                if len(customer)>0:
                    names,emails,phones,last_purchase = customer_list_create(customer)
                    length = len(phones)
                    return render_template('customer_list.html',length=length, name=names, email=emails, phone=phones, date=last_purchase)
                else:
                    flash('!!!  Match NOT Found  !!!')
                    length = 0
                    return render_template('customer_list.html', length=length)
            except Exception as e:
                con.rollback()
                print("Error:",e)
            finally:
                cur.close()
                con.close()
        if searchWith == "phone":
            try:
                con = Connection()
                cur = con.cursor(buffered=True)
                cur.execute("select * from customer where locate('{}',phone)".format(search))
                customer = cur.fetchall()
                if len(customer)>0:
                    names,emails,phones,last_purchase = customer_list_create(customer)
                    length = len(phones)
                    return render_template('customer_list.html',length=length, name=names, email=emails, phone=phones, date=last_purchase)
                else:
                    flash('!!!  Match NOT Found  !!!')
                    length = 0
                    return render_template('customer_list.html', length=length)
            except Exception as e:
                con.rollback()
                print("Error:",e)
            finally:
                cur.close()
                con.close()
    else:
        try:
                con = Connection()
                cur = con.cursor(buffered=True)
                cur.execute("select * from customer")
                customer = cur.fetchall()
                names,emails,phones,last_purchase = customer_list_create(customer)
                length = len(phones)
                return render_template('customer_list.html',length=length, name=names, email=emails, phone=phones, date=last_purchase)
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()

def customer_list_create(customer):
    name_list = []
    email_list =[]
    phone_list = []
    last_purchase = []
    for i in range(len(customer)):
        name_list.append(customer[i][0])
        email_list.append(customer[i][1])
        phone_list.append(customer[i][4])
        try:
            con = Connection()
            cur = con.cursor(buffered=True)
            cur.execute("select date from customer_history where phone = {} order by sl_no desc".format(customer[i][4]))
            date = cur.fetchall()
            if len(date)>0:
                date = date[0][0]
                x = date.split("-")
                year = str(x[0])
                month = str(x[1])
                day = str(x[2])
                new_date = day+"-"+month+"-"+year
                last_purchase.append(new_date)
            else:
                last_purchase.append(None)
        except Exception as e:
            con.rollback()
            print("Error:",e)
        finally:
            cur.close()
            con.close()
            
    return name_list,email_list,phone_list,last_purchase
"""
@app.route('/scan')
def purchase_scan():
    import Smart_Weighing_machine
    print(Smart_Weighing_machine.hx.get_weight_mean(30))
    return redirect('/history')
"""
@app.route('/scan')
def purchase_scan():
    return render_template('scan.html')

if __name__ == "__main__":
    app.debug = True
    app.run()